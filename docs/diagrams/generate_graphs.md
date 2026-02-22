# Generate Graphs

## Architecture Diagram

To generate the architecture diagram, run the following command from the root of the project:

```bash
 uv run docs/diagrams/architecture.py
```

This will create a file named `architecture_diagram.png` in the `docs/diagrams` directory. You can open this file to view the architecture diagram of the project.

# Django apps classes diagrams

To generate the Django apps classes diagrams, run the following command from the root of the project:

### Campaigns app

```bash
 uv run service/manage.py graph_models campaigns -g -o campaigns.dot
```

Then, you can convert the generated `campaigns.dot` file to a PNG image using Graphviz:

```bash
 dot -Tpdf campaigns.dot -Gdpi=300 -o campaigns.pdf
```

### Places app

```bash
 uv run service/manage.py graph_models places -g -o places.dot
```

Then, convert the `places.dot` file to a PNG image:

```bash
 dot -Tpdf places.dot -Gdpi=300 -o places.pdf
```

# DAGs Diagram
To generate the DAGs diagram for the `process_coverage` DAG, run the following command from the root of the project:

```bash
    docker exec -it spectrumsaber-airflow-worker-1 airflow dags show process_coverage --save tmp/process_coverage.dot
    dot -Tpdf tmp/process_coverage.dot -Gdpi=300 -o process_coverage.pdf
```

