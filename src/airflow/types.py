import strawberry
from typing import Optional


@strawberry.input
class KeyValueInput:
    key: str
    value: str


@strawberry.type
class DagParamType:
    name: str
    type: Optional[str]
    description: Optional[str]


@strawberry.type
class DagInfoType:
    dag_id: str
    dag_display_name: Optional[str]
    is_active: Optional[bool]
    is_paused: Optional[bool]
    tags: Optional[list[str]]
    description: Optional[str]
    params: Optional[list[DagParamType]]
