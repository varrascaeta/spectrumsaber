from diagrams import Cluster, Diagram
from diagrams.generic.storage import Storage
from diagrams.onprem.database import PostgreSQL
from diagrams.custom import Custom
from diagrams.programming.language import Python

# Estilos para las fases ETL
extract_style = {
    "bgcolor": "#81C784",
    "style": "rounded",
    "fontsize": "25",
    "fontcolor": "white",
}

transform_style = {
    "bgcolor": "#64B5F6",
    "style": "rounded",
    "fontsize": "25",
    "fontcolor": "white",
}

load_style = {
    "bgcolor": "#E57373",
    "style": "rounded",
    "fontsize": "25",
    "fontcolor": "white",
}

orchestrator_style = {
    "style": "rounded",
    "fontsize": "25",
}

diagram_graph_attr = {
    "splines": "ortho",
    "pad": "0",
    "nodesep": "0.8",
    "ranksep": "1.0",
    "fontsize": "30",
}

node_attr = {
    "fontsize": "20",
}

subcluster_attr = {
    "penwidth": "0",
    "bgcolor": "transparent",
    "fontsize": "30",
    "labeljust": "c",
    "labelloc": "b"
}


with Diagram(
    "Proceso ETL",
    show=True,
    direction="LR",
    graph_attr=diagram_graph_attr,
    node_attr=node_attr,
    filename="etl_process",
):
    
    with Cluster("FTP", graph_attr=subcluster_attr):
        ftp = Storage()
    
    with Cluster("DB", graph_attr=subcluster_attr):
        db = PostgreSQL()
    
    with Cluster("Orquestador", graph_attr=orchestrator_style):
        with Cluster("Extract", graph_attr=extract_style):
            listar = Python("\nListar\narchivos")
            recolectar = Python("\nRecolectar\nmetadatos")
            
            listar >> recolectar
        
        with Cluster("Transform", graph_attr=transform_style):
            normalizar = Python("\nNormalizar\nrutas y\nnombres")
            categorizar = Python("\nCategorizar")
            
            normalizar >> categorizar
        
        with Cluster("Load", graph_attr=load_style):
            cargar = Python("\nCargar en\nmodelos\nrelacionales")
            guardar = Python("\nGuardar en\nla DB")
            
            cargar >> guardar
        
    
    # Flujo principal
    ftp >> listar
    recolectar >> normalizar
    categorizar >> cargar
    guardar >> db
