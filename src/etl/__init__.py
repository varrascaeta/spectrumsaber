"""
ETL package — Airflow-based data ingestion pipeline.

Orchestrates the end-to-end ingestion of CONAE spectroscopy data from
FTP into the Django database:

- operators: Custom Airflow operators (SetupDjango, ScanFTPDirectory)
- tasks:     Reusable Airflow task functions (pattern matching, building,
             committing)
- utils:     FTP directory traversal helpers
- dags:      Four DAGs: process_coverage → process_campaigns →
             process_data_points → process_measurements
"""
