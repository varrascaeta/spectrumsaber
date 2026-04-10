# etl (Airflow ETL pipeline)

## Brief description

The `etl` package contains the Apache Airflow DAGs, custom operators, reusable tasks, and utility functions that drive the data ingestion pipeline. It reads the CONAE FTP directory tree, classifies files using configurable regex rules, and persists structured records into the Django database.

## Purpose

- Orchestrate incremental ingestion of spectral data from the CONAE FTP server.
- Decouple FTP scanning from database writes using the Builder/Director pattern from `server.campaigns`.
- Provide a retry-capable, observable pipeline that can be triggered manually or on a schedule via the Airflow UI.

## Main classes and functions

### `operators.py`

| Name | Kind | Description |
|------|------|-------------|
| `SetupDjango` | `BaseOperator` | Initialises the Django application (`django.setup()`) at the start of every DAG so ORM models are available in subsequent tasks |
| `ScanFTPDirectory` | `BaseOperator` | Lists one level of an FTP directory using `FTPClient.get_dir_data()`; returns a list of `{path, is_dir, name, parent}` dicts; `depth` parameter controls recursion depth |

### `tasks.py`

Airflow `@task`-decorated functions and task-group factories:

| Name | Kind | Description |
|------|------|-------------|
| `check_non_empty_dict(dict_data, key)` | task | Skips downstream if `key` is absent or empty in `dict_data` |
| `match_patterns(file_data, level)` | task | Calls `PathRule.match_files()` to classify a batch of files into `matched`, `unmatched`, and `complimentary` buckets |
| `get_dict_result(data, key)` | task | Extracts a single key from a dict result (used after `match_patterns`) |
| `recurse_complimentary_dirs(file_data)` | task | Walks any directory entries in the complimentary bucket to collect all leaf files |
| `filter_non_empty(files_groups)` | task | Removes empty lists from a list-of-lists before dynamic expansion |
| `build_single(data, director_class)` | task | Constructs one domain object via a director; returns a base64-pickled director |
| `build_multiple(data_list, director_class)` | task | Constructs a list of domain objects; returns a list of encoded directors |
| `commit_director(director_data)` | task | Decodes and commits one director to the database |
| `commit_multiple(directors_data_list)` | task | Decodes and commits a list of directors |
| `process_expanded_by_class_group(...)` | task-group factory | Expands `build_single` + `commit_director` dynamically over a list; optionally recurses into subdirectories |
| `process_multiple_by_class_group(...)` | task-group factory | Applies `get_dict_result` → `build_multiple` → `commit_multiple`; used when a whole batch is processed at once |

### `utils.py`

| Name | Kind | Description |
|------|------|-------------|
| `get_param_from_context(context, param_name)` | function | Safely reads a DAG run configuration parameter |
| `get_bottom_level_file_recursive(ftp_client, path)` | function | Recursively traverses an FTP tree and returns only leaf (non-directory) files with their `parent` path |
| `trigger_dag(dag_id, conf)` | function | Fires a DAG run via the Airflow REST API using credentials from Django settings |

### `dags/process_coverage.py` — DAG `process_coverage`

Scans the FTP root directory and creates `Coverage` records.

```
SetupDjango
  → ScanFTPDirectory (root)
  → match_patterns
  → [matched]   process_expanded_by_class_group → CoverageDirector
  → [unmatched] process_expanded_by_class_group → UnmatchedDirector
```

### `dags/process_campaigns.py` — DAG `process_campaigns`

Parameters: `coverage_name` (default `AGRICULTURA`), `force_reprocess`.

```
SetupDjango
  → ScanFTPDirectory ({coverage_name})
  → get_campaigns_to_process         # filters by scan_complete unless force_reprocess
  → match_patterns
  → [matched]       process_expanded_by_class_group → CampaignDirector
  → [unmatched]     process_expanded_by_class_group → UnmatchedDirector
  → [complimentary] process_expanded_by_class_group → ComplimentaryDirector (recurse_dirs=True)
```

### `dags/process_data_points.py` — DAG `process_data_points`

Parameters: `coverage_name` (default `HIDROLOGIA`), `force_reprocess`.

```
SetupDjango
  → get_campaings_to_scan            # ORM query for unscanned campaigns
  → ScanFTPDirectory.expand          # one scan per campaign (dynamic)
  → get_data_points_to_process.expand
  → filter_non_empty
  → match_patterns.expand
  → [matched/unmatched/complimentary] process_multiple_by_class_group (expand)
```

### `dags/process_measurements.py` — DAG `process_measurements`

Parameters: `coverage_name` (default `HIDROLOGIA`).

```
SetupDjango
  → get_data_points_to_scan          # ORM query for unscanned data points
  → get_measurements.expand          # recursively collect files per data point
  → [matched/complimentary] process_multiple_by_class_group (expand)
```

## Interaction with other modules

| Dependency | How |
|------------|-----|
| `server.campaigns.models` | Tasks query `Campaign`, `DataPoint`, `PathRule` directly via the ORM |
| `server.campaigns.directors` | `build_single` / `build_multiple` look up director classes by name via `get_director_by_class_name` |
| `server.settings` | `SetupDjango` sets `DJANGO_SETTINGS_MODULE`; `utils.trigger_dag` reads `AIRFLOW_WEBSERVER`, `AIRFLOW_USER`, `AIRFLOW_PASSWORD` |
| `spectrumsaber.client.FTPClient` | `ScanFTPDirectory` and `get_bottom_level_file_recursive` use `FTPClient` to list FTP directories |
| Airflow scheduler | DAGs are discovered from `src/etl/dags/`; runtime state (logs, DB) lives in `airflow-home/` |
