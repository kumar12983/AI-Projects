Deployment Docker artifacts for the School Catchment app

This folder contains a simple `Dockerfile` and `docker-compose.yml` to help run the app locally with a PostGIS-enabled PostgreSQL instance for development and testing.

Files:
- `Dockerfile` - builds the Flask app image (based on python:3.11-slim).
- `docker-compose.yml` - starts a `postgis/postgis` database and the `web` service built from the PRD folder.

Quick start (from this folder):

1. Build and start services with docker-compose:

```bash
# run from PRD/deployment/docker
cd PRD/deployment/docker
docker-compose up --build
```

2. The Flask app will be available at `http://localhost:5000`.

Notes & next steps:
- The `Dockerfile` installs a fallback list of Python packages. For production or reproducible builds, add a `PRD/requirements.txt` and modify the `Dockerfile` to `COPY requirements.txt` and `pip install -r requirements.txt`.
- Database initialization: Run the SQL scripts in `PRD/database/setup` (PostGIS extension and materialized view creation) against the running Postgres container. For example:

```bash
# exec into the db container and apply SQL as a superuser
docker exec -it <compose_project>_db_1 bash
psql -U postgres -d gnaf_db -f /path/to/PRD/database/setup/PostGIS/PostGIS.sql
psql -U postgres -d gnaf_db -f /path/to/PRD/database/setup/create_school_address_mv.sql
```

- The docker-compose `build.context` is the `PRD` directory so the image copies `webapp` into the image. Adjust paths if you move files.

If you want, I can:
- Add a `PRD/requirements.txt` and update the `Dockerfile` to use it.
- Add a small `entrypoint.sh` to wait for the DB before starting the web service.
