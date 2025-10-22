# client/graphql_client.py
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

class DjangoGraphQLClient:
    def __init__(self, endpoint, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.client = Client(
            transport=RequestsHTTPTransport(
                url=endpoint,
                headers=headers,
                verify=True,
                retries=3,
            ),
            fetch_schema_from_transport=True,
        )

    def execute(self, query, variables=None):
        return self.client.execute(gql(query), variable_values=variables)
