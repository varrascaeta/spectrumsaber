# Standard imports
import graphene
# Project imports
import resources.campaigns.graphql_schema


class Query(resources.campaigns.graphql_schema.Query, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query)
