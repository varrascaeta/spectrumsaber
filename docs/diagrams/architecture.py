from diagrams import Cluster, Diagram, Edge
from diagrams.generic.network import Firewall
from diagrams.generic.storage import Storage
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.workflow import Airflow
from diagrams.onprem.client import Client, Users, User
from diagrams.programming.framework import Django, GraphQL
from diagrams.programming.language import Python


container_style = {
    "bgcolor": "#90CAF9",
    "style": "rounded",
    "fontsize": "25",
}

django_apps_style = {
    "bgcolor": "#C1E7C2",
    "style": "rounded",
    "fontsize": "30",
}

diagram_graph_attr = {
    "splines": "spline",
    "overlap": "false",
    "fontsize": "30",
    "pad": "0",
}

cluster_attr = {
    "fontsize": "30",
    "style": "rounded",
}

node_attr = {
    "fontsize": "25",
}

subcluster_attr = {
    "penwidth": "0",
    "bgcolor": "transparent",
    "fontsize": "30",
    "labeljust": "c",
    "labelloc": "b"
}

with Diagram(
    show=True,
    direction="LR",
    graph_attr=diagram_graph_attr,
    node_attr=node_attr,
    filename="architecture_diagram",
):
    # transparent cluster for FTP CONAE to group it visually without a border
    with Cluster("FTP CONAE", graph_attr=subcluster_attr):
        ftp_conae = Storage()

    with Cluster("spectrumsaber-db", graph_attr=container_style):
        db_main = PostgreSQL("Postgres")

    with Cluster("Apache Airflow", graph_attr=cluster_attr):
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

        with Cluster("Django ORM", graph_attr=django_apps_style):
            campaigns = Django("campaigns")
            users = Django("users")
            places = Django("places")
            django_admin = Django("admin")
            django_services = [campaigns, users, places, django_admin]

            django_services >> db_main

        dags = Python("DAGs")

        gql_auth >> gql_api >> db_main
        ftp_conae >> dags
        dags >> campaigns
        dags >> places
        triggerer >> dags
  
    with Cluster("Spectrumsaber", graph_attr=cluster_attr):
        with Cluster("CLI", graph_attr=subcluster_attr):
            cli = Python()

        with Cluster("MCP", graph_attr=subcluster_attr):
            mcp = Client()

        cli >> gql_auth
        mcp >> gql_auth

    with Cluster("CONAE", graph_attr=cluster_attr):
        with Cluster("Users", graph_attr=subcluster_attr):
            conae_user = Users()

        with Cluster("Admin", graph_attr=subcluster_attr):
            conae_admin = User()
    
    conae_user >> ftp_conae
    conae_user >> cli
    conae_user >> mcp
    conae_admin >> ftp_conae
    #conae_admin >> django_admin