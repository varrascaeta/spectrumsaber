"""GraphQL types for Airflow DAGs."""

from typing import Any, Optional


class DagParamType:
    """Type for DAG parameters."""

    def __init__(
        self,
        name: str,
        value: Any,
        param_type: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.name = name
        self.value = value
        self.param_type = param_type
        self.description = description


class DagInfoType:
    """Type for DAG information."""

    def __init__(
        self,
        dag_id: str,
        description: Optional[str] = None,
        schedule: Optional[str] = None,
        tags: Optional[list[str]] = None,
        params: Optional[list[DagParamType]] = None,
    ):
        self.dag_id = dag_id
        self.description = description
        self.schedule = schedule
        self.tags = tags or []
        self.params = params or []
