# Spectrumsaber Project Run

## Running the Project

This project uses Docker to run the application. You can run different parts of the application using Docker Compose.

### Running the app and database
1. Run the following command to start the database and the admin:
```bash
    docker compose -f containers/app/docker-compose.yml up --profile app
```

> You can access the database admin at http://localhost:8000/admin/ or the home page at http://localhost:8000/

### Running the database only
Or, if you want to run only the database:
```bash
    docker compose -f containers/app/docker-compose.yml up --profile db
```

### Running airflow services
This command will run the airflow services, such as the web server and scheduler.

```bash
    docker compose -f containers/app/docker-compose.yml up --profile airflow
```

> You can access the airflow web server at http://localhost:8080/

### Running the whole project
If you want to run the whole project, including the database, app, and airflow:
```bash
    docker compose -f containers/app/docker-compose.yml up
```


## Notes

1. If you run any container that is involved with the database, you need to run the following command to create the database and the admin user:
    ```bash
    uv run --env-file environments/local.env python service/manage.py createsuperuser
    ```

2. If you want to rebuild, it is only necessary to rebuild the app. DO NOT delete the volume, otherwise you will lose all the data. To rebuild the whole project, run the following command:
    ```bash
    docker-compose -f containers/app/docker-compose.yml up --build --no-deps spectrumsaber
    ```
> Since we use docker compose with mounted volumes it is not necessary to rebuild the images unless a new dependency is added using `uv install` command.
