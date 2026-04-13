"""
Natural-language to GraphQL translation for the SpectrumSaber system.

Main class:
    Text2GQL -- Converts plain-language questions into executable GraphQL
                queries by combining live schema introspection with an LLM.
                Exposes ``translate(text)`` (returns a query string) and
                ``execute(text)`` (translates and runs in one call).

Helpers:
    _build_schema_summary(introspection_data) -- Converts raw GraphQL
        introspection JSON into a compact, LLM-readable schema description,
        covering query entry points, object/input types, and enums.
    _strip_code_fences(text) -- Removes ```graphql ... ``` or ``` ... ```
        wrappers that some LLMs add around their output.

The module relies on an :class:`~spectrumsaber.llm.LLMProvider` instance
(created via :func:`~spectrumsaber.llm.create_provider`) to generate the
GraphQL from the schema summary and the user's natural-language input.

Usage:
    from spectrumsaber.client import SpectrumSaberClient
    from spectrumsaber.llm import create_provider
    from spectrumsaber.text2gql import Text2GQL

    client = SpectrumSaberClient()
    llm    = create_provider("anthropic", api_key="sk-ant-...")
    t2gql  = Text2GQL(client, llm)

    # Just get the generated query:
    query = t2gql.translate("Get all campaigns from CORDOBA in 2023")

    # Translate AND execute in one call:
    result = t2gql.execute("Get all campaigns from CORDOBA in 2023")
"""

from __future__ import annotations

import logging
import re

from spectrumsaber.llm import LLMProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GraphQL introspection query
# ---------------------------------------------------------------------------

_INTROSPECTION_QUERY = """
{
  __schema {
    queryType { name }
    types {
      name
      kind
      fields(includeDeprecated: false) {
        name
        type {
          name kind
          ofType { name kind ofType { name kind ofType { name kind } } }
        }
        args {
          name
          type {
            name kind
            ofType { name kind ofType { name kind ofType { name kind } } }
          }
        }
      }
      inputFields {
        name
        type {
          name kind
          ofType { name kind ofType { name kind ofType { name kind } } }
        }
      }
      enumValues { name }
    }
  }
}
"""

# Built-in / scalar types to skip when building the schema summary
_SKIP_TYPES = frozenset(
    {
        "String",
        "Int",
        "Float",
        "Boolean",
        "ID",
        "DateTime",
        "Date",
        "UUID",
        "JSONString",
        "Decimal",
        "GenericScalar",
        "Upload",
        "__Schema",
        "__Type",
        "__Field",
        "__InputValue",
        "__EnumValue",
        "__Directive",
        "__DirectiveLocation",
    }
)

# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a GraphQL query generator for the SpectrumSaber spectral data system.

Convert the user's natural language request into a valid GraphQL query.

## Rules
1. Return ONLY the raw GraphQL query string — no markdown, no code
   blocks, no explanation.
2. Use only types and fields defined in the schema below.
3. Always include `id` and `name` in every object selection unless the
   user asks for specific fields only.
4. Apply filters when the user specifies conditions.
5. Prefer the narrowest selection that still answers the question.

## Filter syntax
Filter fields accept plain scalar values — pass the value directly:
  - String fields: `name: "CORDOBA"` (NOT `name: {{ exact: "CORDOBA" }}`)
  - Date fields:   `date: "2023-06-15"` (NOT `date: {{ exact: "..." }}`)
  - ID fields:     `id: "42"`

For date ranges use `dateGte` and `dateLte` as top-level arguments on
the `campaigns` query (NOT inside `filters`):
  `campaigns(dateGte: "2023-01-01", dateLte: "2023-12-31") {{ ... }}`
They can be combined with `filters` freely.

For OR / AND conditions use `OR:`, `AND:`, `NOT:` (same filter type
recursively).

## Data conventions
- **Coverage names** are stored in UPPERCASE (e.g. "CORDOBA", "TUCUMAN").
  Always convert the user's input to uppercase when filtering by `name`.
- **Prefer `normalizedName`** (lowercase) for case-insensitive lookups
  when the user gives a name in mixed case.
- **Campaign names** follow patterns like "12345-20230615-GEO".
- **Category names** (exact values): "Raw Data", "Radiance",
  "Reflectance", "Average Radiance", "Average Reflectance", "Text Data",
  "Text Radiance", "Text Reflectance", "Text Average Radiance",
  "Text Average Reflectance", "Radiance Parabolic Correction",
  "Reflectance Parabolic Correction",
  "Text Radiance Parabolic Correction",
  "Text Reflectance Parabolic Correction".
- Date format in all filter fields: "YYYY-MM-DD"

## Filter syntax examples

Campaigns from a coverage (by normalized lowercase name):
```
query {{
  campaigns(filters: {{ coverage: {{ normalizedName: "cordoba" }} }}) {{
    id name date coverage {{ id name }}
  }}
}}
```

Campaigns within a year range (dateGte/dateLte are top-level args):
```
query {{
  campaigns(
    filters: {{ coverage: {{ name: "CORDOBA" }} }}
    dateGte: "2011-01-01"
    dateLte: "2011-12-31"
  ) {{
    id name date
  }}
}}
```

All coverages:
```
query {{ coverages {{ id name normalizedName }} }}
```

## Schema
{schema}
"""

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def _resolve_type(type_ref: dict) -> str:
    """Recursively resolve a GraphQL type reference to a readable string."""
    if type_ref is None:
        return "Unknown"
    kind = type_ref.get("kind")
    name = type_ref.get("name")
    of_type = type_ref.get("ofType")

    if kind == "NON_NULL":
        return f"{_resolve_type(of_type)}!"
    if kind == "LIST":
        return f"[{_resolve_type(of_type)}]"
    return name or "Unknown"


def _entry_point_lines(
    all_types: list[dict], query_type_name: str
) -> list[str]:
    """Return schema-summary lines for Query entry points."""
    query_type = next(
        (t for t in all_types if t["name"] == query_type_name), None
    )
    if not (query_type and query_type.get("fields")):
        return []

    lines = [f"### {query_type_name} (entry points)"]
    for field in query_type["fields"]:
        args = field.get("args") or []
        arg_str = ""
        if args:
            parts = [f"{a['name']}: {_resolve_type(a['type'])}" for a in args]
            arg_str = f"({', '.join(parts)})"
        ret = _resolve_type(field["type"])
        lines.append(f"  {field['name']}{arg_str}: {ret}")
    lines.append("")
    return lines


def _object_type_lines(
    all_types: list[dict], query_type_name: str
) -> list[str]:
    """Return schema-summary lines for OBJECT and INPUT_OBJECT types."""
    lines: list[str] = []
    for t in all_types:
        name = t["name"]
        kind = t["kind"]
        if name in _SKIP_TYPES or name.startswith("__"):
            continue
        if kind not in ("OBJECT", "INPUT_OBJECT"):
            continue
        if name == query_type_name:
            continue
        fields_src = t.get("fields") or t.get("inputFields") or []
        if not fields_src:
            continue
        lines.append(f"### {name}")
        for f in fields_src:
            lines.append(f"  {f['name']}: {_resolve_type(f['type'])}")
        lines.append("")
    return lines


def _enum_type_lines(all_types: list[dict]) -> list[str]:
    """Return schema-summary lines for ENUM types."""
    lines: list[str] = []
    for t in all_types:
        if t["kind"] != "ENUM" or t["name"].startswith("__"):
            continue
        values = [e["name"] for e in (t.get("enumValues") or [])]
        if values:
            lines.append(f"### {t['name']} (enum)")
            lines.append(f"  Values: {', '.join(values)}")
            lines.append("")
    return lines


def _build_schema_summary(introspection_data: dict) -> str:
    """
    Convert raw introspection JSON into a compact, LLM-friendly schema string.

    Skips internal/built-in types and shows only query-facing types.
    """
    schema = introspection_data.get("__schema", {})
    query_type_name = (schema.get("queryType") or {}).get("name", "Query")
    all_types: list[dict] = schema.get("types", [])

    lines = (
        _entry_point_lines(all_types, query_type_name)
        + _object_type_lines(all_types, query_type_name)
        + _enum_type_lines(all_types)
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class Text2GQL:
    """
    Translates natural language to GraphQL using live schema introspection
    and an LLM provider.

    Args:
        saber_client: An authenticated SpectrumSaberClient.
        llm_provider: Any LLMProvider instance.
        cache_schema: Cache the introspected schema between calls
                      (default: True). Set to False to always re-fetch.
    """

    def __init__(
        self,
        saber_client,
        llm_provider: LLMProvider,
        cache_schema: bool = True,
    ) -> None:
        self.client = saber_client
        self.llm = llm_provider
        self._cache_schema = cache_schema
        self._schema_cache: str | None = None

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def fetch_schema(self) -> str:
        """
        Run the introspection query against the live GraphQL endpoint and
        return a compact, human-readable schema description.

        The result is cached after the first call unless
        ``cache_schema=False``.
        """
        if self._cache_schema and self._schema_cache is not None:
            return self._schema_cache

        logger.debug("Fetching GraphQL schema via introspection")
        result = self.client.query(_INTROSPECTION_QUERY)

        if result.get("errors"):
            raise RuntimeError(
                f"Introspection query failed: {result['errors']}"
            )

        summary = _build_schema_summary(result["data"])

        if self._cache_schema:
            self._schema_cache = summary

        return summary

    def invalidate_schema_cache(self) -> None:
        """Clear the cached schema so the next call fetches it fresh."""
        self._schema_cache = None

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    def translate(self, natural_text: str) -> str:
        """
        Convert a natural language request to a GraphQL query string.

        Args:
            natural_text: User's question or request in plain language.

        Returns:
            A GraphQL query string ready to be passed to
            ``SpectrumSaberClient.query()``.
        """
        schema = self.fetch_schema()
        system_prompt = _SYSTEM_PROMPT.format(schema=schema)
        raw = self.llm.generate(system_prompt, natural_text)

        # Strip markdown code fences if the model wraps the output
        query = _strip_code_fences(raw)
        logger.debug("Generated query:\n%s", query)
        return query

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def execute(self, natural_text: str) -> dict:
        """
        Translate a natural language request and immediately execute it.

        Args:
            natural_text: User's question or request.

        Returns:
            The raw GraphQL response dict
            (``{"data": ..., "errors": ...}``).
        """
        query = self.translate(natural_text)
        logger.info("Executing translated query for: %r", natural_text)
        return self.client.query(query)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _strip_code_fences(text: str) -> str:
    """Remove ```graphql ... ``` or ``` ... ``` wrappers if present."""
    text = text.strip()
    pattern = r"^```(?:graphql|gql)?\s*\n?([\s\S]*?)\n?```$"
    match = re.match(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text
