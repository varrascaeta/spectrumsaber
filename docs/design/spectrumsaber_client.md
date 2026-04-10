# spectrumsaber (CLI client)

## Brief description

The installable `spectrumsaber` package is the project's client library and command-line interface. It connects to the CONAE FTP server to browse spectral data, authenticates against the Django GraphQL API, and optionally translates natural-language questions into GraphQL queries using an LLM.

## Purpose

- Provide a reusable Python client for the SpectrumSaber API usable by scripts and interactive sessions.
- Expose a rich terminal UI for non-programmatic use (`spectrumsaber` CLI command).
- Offer a dedicated text-to-GraphQL entry point (`spectrumsaber-t2gql`) for exploratory data analysis.

## Main classes and functions

### `cfg.py`

| Name | Kind | Description |
|------|------|-------------|
| `FTP_HOST`, `FTP_USER`, `FTP_PASSWORD` | constants | CONAE FTP credentials loaded from environment / `.env` file |
| `GRAPHQL_ENDPOINT` | constant | Target GraphQL URL (default `http://localhost:8000/graphql/`) |
| `GRAPHQL_JWT_TOKEN` | constant | Pre-loaded JWT token (optional) |

### `llm.py`

| Name | Kind | Description |
|------|------|-------------|
| `LLMProvider` | ABC | Abstract interface: `generate(system_prompt, user_message) → str` |
| `AnthropicProvider` | class | Claude implementation (default model: `claude-opus-4-6`) |
| `OpenAIProvider` | class | GPT implementation (default model: `gpt-4o`) |
| `create_provider(name, api_key, **kwargs)` | factory | Instantiate a provider by name string (`"anthropic"` or `"openai"`) |

### `text2gql.py`

| Name | Kind | Description |
|------|------|-------------|
| `Text2GQL` | class | Orchestrates schema introspection + LLM translation |
| `Text2GQL.fetch_schema()` | method | Runs a GraphQL introspection query and converts the result to a compact, LLM-readable schema summary |
| `Text2GQL.translate(text)` | method | Sends schema + user text to the LLM, returns a GraphQL query string |
| `Text2GQL.execute(text)` | method | Calls `translate` then immediately executes the resulting query |
| `Text2GQL.invalidate_schema_cache()` | method | Forces re-introspection on the next call |
| `_build_schema_summary(data)` | function | Converts raw introspection JSON to a token-efficient text representation |

### `client.py`

| Name | Kind | Description |
|------|------|-------------|
| `FTPClient` | class | Context-manager FTP client with directory listing, recursive traversal, and per-line parser |
| `FTPClient.get_dir_data(path)` | method | List one directory level, returns `[{path, is_dir, name, ...}]` |
| `FTPClient.get_files_at_depth(path, max_depth)` | method | Recursive traversal up to `max_depth` levels |
| `SpectrumSaberClient` | class | Authenticated GraphQL client (JWT token management, query execution) |
| `SpectrumSaberClient.login(username, password)` | method | Authenticate and persist tokens |
| `SpectrumSaberClient.query(query, variables)` | method | Execute a raw GraphQL query |
| `SpectrumSaberClient.text2gql(llm_provider)` | method | Create a `Text2GQL` instance bound to this client |
| `RichInteractiveClient` | class | Full-featured terminal shell (Rich UI, multi-line query editor, result export) |
| `CLIClient` | class | Non-interactive programmatic client for scripting and automation |
| `main()` | function | `spectrumsaber` entry point — parses CLI arguments, routes to interactive or batch mode |
| `main_t2gql()` | function | `spectrumsaber-t2gql` entry point — dedicated text-to-GraphQL REPL |

## Interaction with other modules

| Dependency | How |
|------------|-----|
| `server` (Django) | `SpectrumSaberClient` sends HTTP requests to the GraphQL endpoint exposed by the Django server |
| `spectrumsaber.cfg` | All modules read FTP/GraphQL credentials from `cfg.py` |
| `spectrumsaber.llm` | `Text2GQL` delegates generation to whichever `LLMProvider` is injected |
| `spectrumsaber.text2gql` | `SpectrumSaberClient.text2gql()` composes `Text2GQL` with the client as the executor |
| CONAE FTP server | `FTPClient` connects directly over the FTP protocol |
| Anthropic / OpenAI APIs | `AnthropicProvider` and `OpenAIProvider` call external HTTP APIs |
