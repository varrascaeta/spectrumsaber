# Standard imports
import graphene
# Project imports
import src.campaigns.graphql_schema


class Query(src.campaigns.graphql_schema.Query, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query)
