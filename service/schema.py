# Standard imports
import logging
# GQL Auth imports
from gqlauth.core.middlewares import JwtSchema
from gqlauth.user.queries import UserQueries
# Strawberry imports
import strawberry
from strawberry_django.optimizer import DjangoOptimizerExtension
# Project imports
from src.airflow.schema import AirflowMutation, AirflowQuery
from src.campaigns.schema import CampaignQuery
from src.users.schema import AuthMutation

logger = logging.getLogger(__name__)


@strawberry.type
class Query(UserQueries, CampaignQuery, AirflowQuery):
    pass

@strawberry.type
class Mutation(AuthMutation, AirflowMutation):
    pass

# This is essentially the same as strawberries schema though it
# injects the user to `info.context["request"].user`
schema = JwtSchema(
    query=Query,
    mutation=Mutation,
    extensions=[
        DjangoOptimizerExtension,
    ]
)
