# Standard imports
from unittest.mock import MagicMock, Mock, patch

# Third-party imports
import pytest

# Project imports
from spectrumsaber.llm import (
    AnthropicProvider,
    OpenAIProvider,
    create_provider,
)
from spectrumsaber.text2gql import (
    Text2GQL,
    _build_schema_summary,
    _entry_point_lines,
    _object_type_lines,
    _resolve_type,
    _strip_code_fences,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_INTROSPECTION = {
    "__schema": {
        "queryType": {"name": "Query"},
        "types": [
            {
                "name": "Query",
                "kind": "OBJECT",
                "fields": [
                    {
                        "name": "coverages",
                        "type": {
                            "name": None,
                            "kind": "LIST",
                            "ofType": {
                                "name": "CoverageType",
                                "kind": "OBJECT",
                                "ofType": None,
                                "ofType": None,
                            },
                        },
                        "args": [
                            {
                                "name": "filters",
                                "type": {
                                    "name": "CoverageFilter",
                                    "kind": "INPUT_OBJECT",
                                    "ofType": None,
                                },
                            }
                        ],
                    },
                    {
                        "name": "campaigns",
                        "type": {
                            "name": None,
                            "kind": "LIST",
                            "ofType": {
                                "name": "CampaignType",
                                "kind": "OBJECT",
                                "ofType": None,
                            },
                        },
                        "args": [],
                    },
                ],
                "inputFields": None,
                "enumValues": None,
            },
            {
                "name": "CoverageType",
                "kind": "OBJECT",
                "fields": [
                    {
                        "name": "id",
                        "type": {
                            "name": "ID",
                            "kind": "SCALAR",
                            "ofType": None,
                        },
                        "args": [],
                    },
                    {
                        "name": "name",
                        "type": {
                            "name": "String",
                            "kind": "SCALAR",
                            "ofType": None,
                        },
                        "args": [],
                    },
                    {
                        "name": "normalizedName",
                        "type": {
                            "name": "String",
                            "kind": "SCALAR",
                            "ofType": None,
                        },
                        "args": [],
                    },
                ],
                "inputFields": None,
                "enumValues": None,
            },
            {
                "name": "CoverageFilter",
                "kind": "INPUT_OBJECT",
                "fields": None,
                "inputFields": [
                    {
                        "name": "name",
                        "type": {
                            "name": "StrFilterLookup",
                            "kind": "INPUT_OBJECT",
                            "ofType": None,
                        },
                    }
                ],
                "enumValues": None,
            },
            # Built-in scalar — should be skipped
            {
                "name": "String",
                "kind": "SCALAR",
                "fields": None,
                "inputFields": None,
                "enumValues": None,
            },
            # Introspection type — should be skipped
            {
                "name": "__Schema",
                "kind": "OBJECT",
                "fields": [],
                "inputFields": None,
                "enumValues": None,
            },
            # Enum type
            {
                "name": "OrderingDirection",
                "kind": "ENUM",
                "fields": None,
                "inputFields": None,
                "enumValues": [{"name": "ASC"}, {"name": "DESC"}],
            },
        ],
    }
}

SAMPLE_INTROSPECTION_RESPONSE = {"data": SAMPLE_INTROSPECTION}


@pytest.fixture
def mock_saber_client():
    client = Mock()
    client.query.return_value = SAMPLE_INTROSPECTION_RESPONSE
    return client


@pytest.fixture
def mock_llm():
    provider = Mock()
    provider.generate.return_value = (
        "query { coverages { id name normalizedName } }"
    )
    return provider


@pytest.fixture
def text2gql(mock_saber_client, mock_llm):
    return Text2GQL(mock_saber_client, mock_llm)


# ---------------------------------------------------------------------------
# _strip_code_fences
# ---------------------------------------------------------------------------


class TestStripCodeFences:
    def test_plain_query_unchanged(self):
        q = "query { coverages { id name } }"
        assert _strip_code_fences(q) == q

    def test_strips_graphql_fence(self):
        raw = "```graphql\nquery { coverages { id name } }\n```"
        assert _strip_code_fences(raw) == "query { coverages { id name } }"

    def test_strips_gql_fence(self):
        raw = "```gql\nquery { coverages { id } }\n```"
        assert _strip_code_fences(raw) == "query { coverages { id } }"

    def test_strips_plain_fence(self):
        raw = "```\nquery { coverages { id } }\n```"
        assert _strip_code_fences(raw) == "query { coverages { id } }"

    def test_strips_surrounding_whitespace(self):
        raw = "  query { coverages { id } }  "
        assert _strip_code_fences(raw) == "query { coverages { id } }"

    def test_multiline_query_in_fence(self):
        raw = "```graphql\nquery {\n  coverages {\n    id\n  }\n}\n```"
        result = _strip_code_fences(raw)
        assert "coverages" in result
        assert "```" not in result


# ---------------------------------------------------------------------------
# _build_schema_summary
# ---------------------------------------------------------------------------


class TestBuildSchemaSummary:
    def test_includes_query_entry_points(self):
        summary = _build_schema_summary(SAMPLE_INTROSPECTION)
        assert "coverages" in summary
        assert "campaigns" in summary

    def test_includes_object_type_fields(self):
        summary = _build_schema_summary(SAMPLE_INTROSPECTION)
        assert "CoverageType" in summary
        assert "normalizedName" in summary

    def test_includes_input_type(self):
        summary = _build_schema_summary(SAMPLE_INTROSPECTION)
        assert "CoverageFilter" in summary

    def test_skips_builtin_scalars(self):
        summary = _build_schema_summary(SAMPLE_INTROSPECTION)
        # "String" should not appear as a standalone type section
        lines = summary.splitlines()
        assert not any(line.strip() == "### String" for line in lines)

    def test_skips_introspection_types(self):
        summary = _build_schema_summary(SAMPLE_INTROSPECTION)
        assert "__Schema" not in summary

    def test_includes_enum_values(self):
        summary = _build_schema_summary(SAMPLE_INTROSPECTION)
        assert "OrderingDirection" in summary
        assert "ASC" in summary
        assert "DESC" in summary

    def test_returns_string(self):
        result = _build_schema_summary(SAMPLE_INTROSPECTION)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# LLM providers
# ---------------------------------------------------------------------------


class TestCreateProvider:
    def test_create_anthropic_provider(self):
        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = create_provider("anthropic", api_key="sk-ant-test")
        assert isinstance(provider, AnthropicProvider)

    def test_create_openai_provider(self):
        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            provider = create_provider("openai", api_key="sk-test")
        assert isinstance(provider, OpenAIProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider("gemini", api_key="key")

    def test_model_kwarg_forwarded_to_anthropic(self):
        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = create_provider(
                "anthropic", api_key="sk-ant-test", model="claude-haiku-4-5"
            )
        assert provider.model == "claude-haiku-4-5"

    def test_model_kwarg_forwarded_to_openai(self):
        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            provider = create_provider(
                "openai", api_key="sk-test", model="gpt-4o-mini"
            )
        assert provider.model == "gpt-4o-mini"


class TestAnthropicProvider:
    def test_missing_sdk_raises_import_error(self):
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(ImportError, match="anthropic"):
                AnthropicProvider(api_key="sk-ant-test")

    def test_generate_calls_messages_create(self):
        mock_anthropic = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="query { coverages { id } }")]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = (
            mock_message
        )

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="sk-ant-test")
            result = provider.generate("system prompt", "user message")

        assert result == "query { coverages { id } }"
        create = mock_anthropic.Anthropic.return_value.messages.create
        create.assert_called_once()

    def test_generate_passes_system_and_user(self):
        mock_anthropic = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="query { campaigns { id } }")]
        create = mock_anthropic.Anthropic.return_value.messages.create
        create.return_value = mock_message

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="sk-ant-test")
            provider.generate("my system", "my user")

        call_kwargs = create.call_args.kwargs
        assert call_kwargs["system"] == "my system"
        assert call_kwargs["messages"][0]["content"] == "my user"


class TestOpenAIProvider:
    def test_missing_sdk_raises_import_error(self):
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(ImportError, match="openai"):
                OpenAIProvider(api_key="sk-test")

    def test_generate_calls_chat_completions(self):
        mock_openai = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "query { coverages { id } }"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        completions = mock_openai.OpenAI.return_value.chat.completions
        completions.create.return_value = mock_response

        with patch.dict("sys.modules", {"openai": mock_openai}):
            provider = OpenAIProvider(api_key="sk-test")
            result = provider.generate("system", "user")

        assert result == "query { coverages { id } }"

    def test_generate_passes_system_and_user_roles(self):
        mock_openai = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "query { campaigns { id } }"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        create = mock_openai.OpenAI.return_value.chat.completions.create
        create.return_value = mock_response

        with patch.dict("sys.modules", {"openai": mock_openai}):
            provider = OpenAIProvider(api_key="sk-test")
            provider.generate("system text", "user text")

        messages = create.call_args.kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "system text"}
        assert messages[1] == {"role": "user", "content": "user text"}


# ---------------------------------------------------------------------------
# Text2GQL
# ---------------------------------------------------------------------------


class TestText2GQLFetchSchema:
    def test_fetch_schema_runs_introspection(
        self, text2gql, mock_saber_client
    ):
        text2gql.fetch_schema()
        mock_saber_client.query.assert_called_once()
        call_arg = mock_saber_client.query.call_args[0][0]
        assert "__schema" in call_arg

    def test_fetch_schema_returns_string(self, text2gql):
        result = text2gql.fetch_schema()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fetch_schema_is_cached_by_default(
        self, text2gql, mock_saber_client
    ):
        text2gql.fetch_schema()
        text2gql.fetch_schema()
        # Second call should use cache — only one HTTP call
        assert mock_saber_client.query.call_count == 1

    def test_fetch_schema_no_cache_when_disabled(
        self, mock_saber_client, mock_llm
    ):
        t2gql = Text2GQL(mock_saber_client, mock_llm, cache_schema=False)
        t2gql.fetch_schema()
        t2gql.fetch_schema()
        assert mock_saber_client.query.call_count == 2

    def test_invalidate_schema_cache_forces_refetch(
        self, text2gql, mock_saber_client
    ):
        text2gql.fetch_schema()
        text2gql.invalidate_schema_cache()
        text2gql.fetch_schema()
        assert mock_saber_client.query.call_count == 2

    def test_fetch_schema_raises_on_introspection_error(
        self, mock_saber_client, mock_llm
    ):
        mock_saber_client.query.return_value = {
            "errors": [{"message": "Not authorized"}]
        }
        t2gql = Text2GQL(mock_saber_client, mock_llm)
        with pytest.raises(RuntimeError, match="Introspection query failed"):
            t2gql.fetch_schema()


class TestText2GQLTranslate:
    def test_translate_returns_string(self, text2gql):
        result = text2gql.translate("Get all coverages")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_translate_calls_llm_generate(self, text2gql, mock_llm):
        text2gql.translate("Get all coverages")
        mock_llm.generate.assert_called_once()

    def test_translate_passes_natural_text_to_llm(self, text2gql, mock_llm):
        text2gql.translate("List all campaigns from CORDOBA")
        user_arg = mock_llm.generate.call_args[0][1]
        assert user_arg == "List all campaigns from CORDOBA"

    def test_translate_includes_schema_in_system_prompt(
        self, text2gql, mock_llm
    ):
        text2gql.translate("Get all coverages")
        system_arg = mock_llm.generate.call_args[0][0]
        # System prompt must contain schema content (e.g. entry points)
        assert "coverages" in system_arg

    def test_translate_strips_markdown_fences(
        self, mock_saber_client, mock_llm
    ):
        mock_llm.generate.return_value = (
            "```graphql\nquery { coverages { id } }\n```"
        )
        t2gql = Text2GQL(mock_saber_client, mock_llm)
        result = t2gql.translate("Get coverages")
        assert "```" not in result
        assert "coverages" in result

    def test_translate_coverage_convention_in_prompt(self, text2gql, mock_llm):
        text2gql.translate("anything")
        system_arg = mock_llm.generate.call_args[0][0]
        assert "UPPERCASE" in system_arg or "uppercase" in system_arg.lower()

    def test_translate_normalized_name_hint_in_prompt(
        self, text2gql, mock_llm
    ):
        text2gql.translate("anything")
        system_arg = mock_llm.generate.call_args[0][0]
        # The prompt uses camelCase to match the schema field name
        assert "normalizedName" in system_arg


class TestText2GQLExecute:
    def test_execute_returns_dict(self, text2gql, mock_saber_client):
        mock_saber_client.query.side_effect = [
            SAMPLE_INTROSPECTION_RESPONSE,
            {"data": {"coverages": [{"id": "1", "name": "CORDOBA"}]}},
        ]
        result = text2gql.execute("Get all coverages")
        assert isinstance(result, dict)

    def test_execute_calls_client_query_with_translated_query(
        self, mock_saber_client, mock_llm
    ):
        generated_query = "query { coverages { id name } }"
        mock_llm.generate.return_value = generated_query
        mock_saber_client.query.side_effect = [
            SAMPLE_INTROSPECTION_RESPONSE,
            {"data": {"coverages": []}},
        ]

        t2gql = Text2GQL(mock_saber_client, mock_llm)
        t2gql.execute("Get coverages")

        # Second call should be the actual GQL execution
        second_call_arg = mock_saber_client.query.call_args_list[1][0][0]
        assert second_call_arg == generated_query

    def test_execute_uses_cached_schema_on_second_call(
        self, mock_saber_client, mock_llm
    ):
        mock_saber_client.query.side_effect = [
            SAMPLE_INTROSPECTION_RESPONSE,
            {"data": {"coverages": []}},
            {"data": {"coverages": []}},
        ]
        mock_llm.generate.return_value = "query { coverages { id } }"

        t2gql = Text2GQL(mock_saber_client, mock_llm)
        t2gql.execute("Get coverages")
        t2gql.execute("Get coverages again")

        # Introspection runs once; two executes = 3 total (1 intro + 2 gql)
        assert mock_saber_client.query.call_count == 3

    def test_execute_propagates_graphql_errors(
        self, mock_saber_client, mock_llm
    ):
        mock_saber_client.query.side_effect = [
            SAMPLE_INTROSPECTION_RESPONSE,
            {"data": None, "errors": [{"message": "Field not found"}]},
        ]
        mock_llm.generate.return_value = "query { invalid { field } }"

        t2gql = Text2GQL(mock_saber_client, mock_llm)
        result = t2gql.execute("Something invalid")

        # Errors are passed through, not raised — caller decides how to handle
        assert "errors" in result

    def test_full_flow_end_to_end(self, mock_saber_client, mock_llm):
        """
        Simulates the complete text → schema → LLM → GQL → execute pipeline
        with all dependencies mocked.
        """
        expected_campaigns = [
            {"id": "42", "name": "12345-20230615-CORD"},
            {"id": "43", "name": "67890-20230710-CORD"},
        ]
        mock_saber_client.query.side_effect = [
            # 1. Introspection response
            SAMPLE_INTROSPECTION_RESPONSE,
            # 2. Actual query execution response
            {"data": {"campaigns": expected_campaigns}},
        ]
        mock_llm.generate.return_value = (
            "query { campaigns("
            'filters: { coverage: { name: "CORDOBA" } }'
            ") { id name } }"
        )

        t2gql = Text2GQL(mock_saber_client, mock_llm)
        result = t2gql.execute("List all campaigns from the CORDOBA coverage")

        assert result["data"]["campaigns"] == expected_campaigns
        # LLM received a system prompt (with schema) and the user text
        llm_call = mock_llm.generate.call_args
        assert "CORDOBA" in llm_call[0][1]
        assert "coverages" in llm_call[0][0]  # schema was embedded


# ---------------------------------------------------------------------------
# _resolve_type / helper edge cases
# ---------------------------------------------------------------------------


class TestResolveTypeEdgeCases:
    def test_resolve_type_none_returns_unknown(self):
        assert _resolve_type(None) == "Unknown"

    def test_resolve_type_non_null(self):
        type_ref = {
            "kind": "NON_NULL",
            "name": None,
            "ofType": {"kind": "SCALAR", "name": "String", "ofType": None},
        }
        assert _resolve_type(type_ref) == "String!"

    def test_entry_point_lines_returns_empty_when_no_types(self):
        assert _entry_point_lines([], "Query") == []

    def test_entry_point_lines_returns_empty_when_query_type_has_no_fields(
        self,
    ):
        types = [{"name": "Query", "kind": "OBJECT", "fields": None}]
        assert _entry_point_lines(types, "Query") == []

    def test_object_type_lines_skips_type_with_no_fields(self):
        types = [
            {
                "name": "EmptyType",
                "kind": "OBJECT",
                "fields": None,
                "inputFields": None,
            }
        ]
        assert _object_type_lines(types, "Query") == []
