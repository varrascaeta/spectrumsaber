from airflow import DAG

from src.utils import get_dirs_to_process

def dynamic_scan_dag(dag_id, schedule_interval, start_date, ftp_path):
    dag = DAG(dag_id, schedule_interval=schedule_interval, start_date=start_date)
    # define tasks
    subdirs_to_scan = get_dirs_to_process(ftp_path)
    
    for subdir in subdirs_to_scan:
        task = ScanFTPDirectory(
            task_id=f"scan_{subdir}",
            ftp_path=subdir,
            dag=dag
        )
        task1 >> task
    task1 >> task2
    return dag