# client/airflow_client.py
import requests

class AirflowClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)

    def trigger_dag(self, dag_id, conf=None):
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns"
        data = {"conf": conf or {}}
        response = requests.post(url, auth=self.auth, json=data)
        response.raise_for_status()
        return response.json()
