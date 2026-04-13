# server (Django application)

## Brief description

The `server` package is the Django project that hosts the SpectrumSaber web API. It provides a GraphQL endpoint for querying spectral campaign data, JWT-based user authentication, and a Django Admin interface for data management.

## Purpose

- Persist all spectral data produced by the ETL pipeline in a PostgreSQL database.
- Expose a typed GraphQL API consumed by the CLI client and any third-party integrations.
- Provide Django Admin pages for operators to inspect ingested data, manage users, and configure pattern-matching rules.

## Main classes and functions

### `settings.py`

Central Django configuration. Key settings:

| Setting | Value / purpose |
|---------|-----------------|
| `INSTALLED_APPS` | Registers `campaigns`, `places`, `users` apps plus Strawberry and gqlauth |
| `DATABASES` | PostgreSQL, credentials from environment variables |
| `GQL_AUTH` | JWT expiration, captcha disabled, activation email disabled |
| `AIRFLOW_*` | Credentials and webserver URL used by `etl.utils.trigger_dag` |

### `schema.py`

| Name | Kind | Description |
|------|------|-------------|
| `Query` | strawberry type | Inherits `UserQueries` (gqlauth) + `CampaignQuery` |
| `Mutation` | strawberry type | Inherits `AuthMutation` |
| `schema` | `JwtSchema` | Root schema instance with `DjangoOptimizerExtension` (N+1 protection) |

### `campaigns/models.py`

Core domain models representing the FTP directory hierarchy:

| Name | Kind | Description |
|------|------|-------------|
| `BaseFile` | abstract model | Common fields for all file-based entities: `path`, `name`, `metadata`, `scan_complete`, `last_synced_at` |
| `Coverage` | model | Top-level geographic coverage area |
| `Campaign` | model | Measurement campaign under a `Coverage`; has `date`, `external_id`, FK to `District` |
| `DataPoint` | model | Single measurement point within a `Campaign`; has `latitude`, `longitude`, `order` |
| `Measurement` | model | Spectral data file linked to a `DataPoint` and a `Category` |
| `ComplimentaryData` | model | Supporting files (photos, spreadsheets) linked to a `Campaign` or `DataPoint` |
| `Category` | model | Measurement category (Radiance, Reflectance, etc.) |
| `PathRule` | model | Regex rule that classifies FTP filenames into a model level |
| `UnmatchedFile` | model | Files that matched no `PathRule`; promoted once a rule is later added |
| `CategoryType` | static class | Enum-like constants + alias lookup for category names |
| `ComplimentaryDataType` | static class | Enum-like constants + alias lookup for complementary file types |

### `campaigns/builders.py`

Builder pattern — one builder per model, all extending `BaseBuilder`:

| Name | Builds |
|------|--------|
| `CoverageBuilder` | `Coverage` |
| `CampaignBuilder` | `Campaign` (with date parsing + district resolution) |
| `DataPointBuilder` | `DataPoint` |
| `MeasurementBuilder` | `Measurement` |
| `ComplimentaryDataBuilder` | `ComplimentaryData` |
| `UnmatchedBuilder` | `UnmatchedFile` |

### `campaigns/directors.py`

Director pattern — one director per model orchestrating builder calls:

| Name | Directs |
|------|---------|
| `CoverageDirector` | `CoverageBuilder` |
| `CampaignDirector` | `CampaignBuilder` |
| `DataPointDirector` | `DataPointBuilder` |
| `MeasurementDirector` | `MeasurementBuilder` |
| `ComplimentaryDirector` | `ComplimentaryDataBuilder` |
| `UnmatchedDirector` | `UnmatchedBuilder` |
| `get_director_by_class_name(name)` | factory | Returns director class by string name (used by ETL tasks) |

### `campaigns/schema.py`

| Name | Kind | Description |
|------|------|-------------|
| `CampaignQuery` | strawberry type | GraphQL queries for all campaign-domain entities; all queries require authentication |

### `campaigns/gql_types.py`

Strawberry-Django filter and output types for every campaign model (`CoverageType`, `CampaignType`, `DataPointType`, `MeasurementType`, `CategoryType`, and their corresponding `*Filter` types).

### `campaigns/signals.py`

`match_new_patterns` — `post_save` receiver on `PathRule`. When a new rule is saved, it immediately attempts to reclassify existing `UnmatchedFile` records.

### `places/models.py`

Geographic hierarchy used by `Campaign`:

| Name | Fields |
|------|--------|
| `Country` | `name`, `code` |
| `Province` | `name`, `code`, FK `country` |
| `District` | `name`, `code`, FK `province` |

### `users/models.py`

| Name | Kind | Description |
|------|------|-------------|
| `SpectrumsaberUser` | model | Custom `AbstractUser`; requires `email`, `first_name`, `last_name` |

### `users/schema.py`

| Name | Kind | Description |
|------|------|-------------|
| `AuthMutation` | strawberry type | Exposes gqlauth mutations: register, login (`token_auth`), refresh token, password reset, etc. |

## Interaction with other modules

| Dependency | How |
|------------|-----|
| `etl` | ETL tasks call `get_director_by_class_name` and execute builders/directors to persist FTP data |
| `spectrumsaber` (CLI) | `SpectrumSaberClient` sends GraphQL HTTP requests to `server.urls` |
| `gqlauth` | Provides JWT token generation, refresh, and middleware |
| `strawberry-django` | Maps Django models to GraphQL types and applies query optimization |
| PostgreSQL | All domain data is stored; credentials from environment variables |
