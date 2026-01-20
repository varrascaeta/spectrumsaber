from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.workflow import Airflow
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.programming.framework import Django, GraphQL
from diagrams.programming.language import Python
from diagrams.generic.network import Firewall
from diagrams.generic.storage import Storage

container_style = {
    "bgcolor": "#90CAF9",
    "style": "rounded",
}

django_apps_style = {
    "bgcolor": "#C1E7C2",
    "style": "rounded",

}
graph_attr = {
    "splines": "ortho",
    "nodesep": "0.5",
    "ranksep": "1.0",
    "concentrate": "true",
    "overlap": "false",
}

with Diagram("Spectrumsaber Architecture", show=False, direction="LR", graph_attr=graph_attr):

    client = Python("client.py")
    ftp_conae = Storage("FTP CONAE")

    with Cluster("spectrumsaber-db", graph_attr=container_style):
        db_main = PostgreSQL("Postgres")

    with Cluster("Apache Airflow"):
        with Cluster("redis", graph_attr=container_style):
            af_redis = Redis("redis")
            
        with Cluster("airflow-db", graph_attr=container_style):
            af_db = PostgreSQL("db")

        with Cluster("airflow-scheduler", graph_attr=container_style):
            scheduler = Airflow("scheduler")

        with Cluster("airflow-webserver", graph_attr=container_style):
            webserver = Airflow("webserver")

        with Cluster("airflow-worker", graph_attr=container_style):
            workers = Airflow("worker")
        
        with Cluster("airflow-triggerer", graph_attr=container_style):
            triggerer = Airflow("triggerer")

        af_redis - af_db
        af_db - scheduler
        af_db - webserver
        scheduler - workers
        scheduler - triggerer

    with Cluster("spectrumsaber-app", graph_attr=container_style):
        gql_api = GraphQL("GraphQL API")
        gql_auth = Firewall("GQL Auth")
        
        with Cluster("Django Apps", graph_attr=django_apps_style):
            campaigns = Django("campaigns")
            users = Django("users")
            places = Django("places")
            django_services = [campaigns, users, places]
        
        dags = Python("airflow/dags")
        
        gql_api >> django_services
        gql_auth >> users
        dags >> gql_api

    client >> ftp_conae
    client >> gql_auth
    ftp_conae >> dags
    webserver >> gql_api
    triggerer >> dags
    django_services >> db_main