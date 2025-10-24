# Standard imports
import logging
# GQL Auth imports
from gqlauth.core.types_ import GQLAuthError, GQLAuthErrors
from gqlauth.core.utils import get_user
from gqlauth.user.queries import UserQueries
# Strawberry imports
import strawberry
from strawberry.types import Info
from strawberry.scalars import JSON
# Project imports
from src.airflow.types import DagInfoType, KeyValueInput
from src.airflow.utils import trigger_dag, get_dag_info, get_dags

logger = logging.getLogger(__name__)


@strawberry.type
class AirflowQuery:
    @strawberry.field
    def get_dags(self, info: Info) -> list[DagInfoType] | None:
        """
        Get information about a DAG in Airflow, requires JWT auth.
        """
        user = get_user(info)
        if not user.is_authenticated:
            raise GQLAuthError(code=GQLAuthErrors.UNAUTHENTICATED)
        result = get_dags()
        return result

    @strawberry.field
    def get_dag_info(self, info: Info, dag_id: str) -> DagInfoType | None:
        """
        Get information about a DAG in Airflow, requires JWT auth.
        """
        user = get_user(info)
        if not user.is_authenticated:
            raise GQLAuthError(code=GQLAuthErrors.UNAUTHENTICATED)
        result = get_dag_info(dag_id)
        return result


@strawberry.type
class AirflowMutation:
    @strawberry.field
    def trigger_dag(self, info: Info, dag_id: str, params: list[KeyValueInput]) -> str:
        """
        Trigger a DAG in Airflow, requires JWT auth.
        """
        user = get_user(info)
        if not user.is_authenticated:
            raise GQLAuthError(code=GQLAuthErrors.UNAUTHENTICATED)
        conf = {
            "triggered_by": info.context.request.user.username,
        }
        if params:
            conf.update({p.key: p.value for p in params})
        return trigger_dag(dag_id, conf)