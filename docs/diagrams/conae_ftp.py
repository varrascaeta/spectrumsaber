from diagrams import Cluster, Diagram, Edge, Node

# Estilos para los diferentes tipos de nodos
id_style = {
    "bgcolor": "#5DADE2",
    "style": "rounded",
    "fontsize": "20",
    "fontcolor": "white",
}

intermediate_style = {
    "bgcolor": "#9CCC65",
    "style": "rounded",
    "fontsize": "20",
    "fontcolor": "white",
}

measurement_style = {
    "bgcolor": "#9575CD",
    "style": "rounded",
    "fontsize": "20",
    "fontcolor": "white",
}

data_type_style = {
    "bgcolor": "#4DD0E1",
    "style": "rounded",
    "fontsize": "20",
    "fontcolor": "black",
}

file_format_style = {
    "bgcolor": "#FFB74D",
    "style": "rounded",
    "fontsize": "20",
    "fontcolor": "black",
}

diagram_graph_attr = {
    "splines": "spline",
    "pad": "0",
    "nodesep": "0.6",
    "ranksep": "1.2",
    "fontsize": "25",
}

node_attr = {
    "fontsize": "22",
}

subcluster_attr = {
    "penwidth": "0",
    "bgcolor": "transparent",
    "fontsize": "25",
}


with Diagram(
    show=True,
    direction="LR",
    graph_attr=diagram_graph_attr,
    node_attr=node_attr,
    filename="conae_ftp_structure",
):
    # Nodo inicial
    with Cluster("ID-aaaammdd-sitio", graph_attr=id_style):
        id_node = Node("", shape="point", style="invis")
    
    # Rama 1: Datos complementarios
    with Cluster("Datos complementarios", graph_attr=intermediate_style):
        datos_comp = Node("", shape="point", style="invis")
    
    # Sub-ramas de Datos complementarios
    with Cluster("Fotos", graph_attr=measurement_style):
        fotos = Node("", shape="point", style="invis")
    
    with Cluster("Punto-N", graph_attr=data_type_style):
        punto_n_1 = Node("", shape="point", style="invis")
    
    with Cluster("archivo jpg", graph_attr=file_format_style):
        jpg = Node("", shape="point", style="invis")
    
    with Cluster("Instrumento", graph_attr=measurement_style):
        instrumento = Node("", shape="point", style="invis")
    
    with Cluster("archivo doc", graph_attr=file_format_style):
        doc = Node("", shape="point", style="invis")
    
    with Cluster("Planilla Campo", graph_attr=measurement_style):
        planilla_campo = Node("", shape="point", style="invis")
    
    with Cluster("archivo xls", graph_attr=file_format_style):
        xls_1 = Node("", shape="point", style="invis")
    
    with Cluster("Planilla Laboratorio", graph_attr=measurement_style):
        planilla_lab = Node("", shape="point", style="invis")
    
    with Cluster("archivo xls", graph_attr=file_format_style):
        xls_2 = Node("", shape="point", style="invis")
    
    # Rama 2: Punto-N
    with Cluster("Punto-N", graph_attr=intermediate_style):
        punto_n_2 = Node("", shape="point", style="invis")
    
    # Sub-rama 2.a: Fotometría
    with Cluster("Fotometría", graph_attr=measurement_style):
        fotometria = Node("", shape="point", style="invis")
    
    with Cluster("formato txt", graph_attr=file_format_style):
        txt = Node("", shape="point", style="invis")
    
    # Sub-rama 2.b: Radiometría
    with Cluster("Radiometría", graph_attr=measurement_style):
        radiometria = Node("", shape="point", style="invis")
    
    # Tipos de datos de radiometría
    with Cluster("Dato Crudo", graph_attr=data_type_style):
        dato_crudo = Node("", shape="point", style="invis")
    
    with Cluster("extensión .asd", graph_attr=file_format_style):
        asd = Node("", shape="point", style="invis")
    
    with Cluster("Radiancia", graph_attr=data_type_style):
        radiancia = Node("", shape="point", style="invis")
    
    with Cluster("extensión .rad", graph_attr=file_format_style):
        rad = Node("", shape="point", style="invis")
    
    with Cluster("Radiancia promedio", graph_attr=data_type_style):
        radiancia_prom = Node("", shape="point", style="invis")
    
    with Cluster("extensión .rad.md", graph_attr=file_format_style):
        rad_md = Node("", shape="point", style="invis")
    
    with Cluster("Reflectancia", graph_attr=data_type_style):
        reflectancia = Node("", shape="point", style="invis")
    
    with Cluster("extensión .rts", graph_attr=file_format_style):
        rts = Node("", shape="point", style="invis")
    
    with Cluster("Texto Radiancia", graph_attr=data_type_style):
        texto_radiancia = Node("", shape="point", style="invis")
    
    with Cluster("archivo.rad en formato texto .rad.txt", graph_attr=file_format_style):
        rad_txt = Node("", shape="point", style="invis")
    
    with Cluster("Texto Radiancia promedio", graph_attr=data_type_style):
        texto_radiancia_prom = Node("", shape="point", style="invis")
    
    with Cluster("archivo.rad.md en formato texto .rad.md.txt", graph_attr=file_format_style):
        rad_md_txt = Node("", shape="point", style="invis")
    
    with Cluster("Texto Reflectancia", graph_attr=data_type_style):
        texto_reflectancia = Node("", shape="point", style="invis")
    
    with Cluster("archivo.rts en formato texto .rts.txt", graph_attr=file_format_style):
        rts_txt = Node("", shape="point", style="invis")
    
    # Conexiones principales
    id_node >> datos_comp
    id_node >> punto_n_2
    
    # Conexiones de Datos complementarios
    datos_comp >> fotos >> punto_n_1 >> jpg
    datos_comp >> instrumento >> doc
    datos_comp >> planilla_campo >> xls_1
    datos_comp >> planilla_lab >> xls_2
    
    # Conexiones de Punto-N
    punto_n_2 >> fotometria >> txt
    punto_n_2 >> radiometria
    
    # Conexiones de Radiometría
    radiometria >> dato_crudo >> asd
    radiometria >> radiancia >> rad
    radiometria >> radiancia_prom >> rad_md
    radiometria >> reflectancia >> rts
    radiometria >> texto_radiancia >> rad_txt
    radiometria >> texto_radiancia_prom >> rad_md_txt
    radiometria >> texto_reflectancia >> rts_txt
