# Required Dependencies

This file lists the software, database extensions, Python packages, and optional tooling required to run the School Catchment web app found under `PRD/webapp`.

**System**:
- **OS**: Linux (Ubuntu 20.04+ recommended) or Windows 10/11 (server setups supported).
- **Python**: 3.10+ (3.11 recommended). Install `python3`, `python3-venv`, `python3-dev`.
- **Build tools** (for building binary wheels): `build-essential`, `gcc`, `make` (Debian/Ubuntu). On Windows install Visual C++ Build Tools.

**PostgreSQL / Geospatial**:
- **PostgreSQL**: 12+ (match production requirements). Install server and `psql` client.
- **PostGIS**: PostGIS extension required (script: [PRD/database/setup/PostGIS/PostGIS.sql](PRD/database/setup/PostGIS/PostGIS.sql#L1-L40)). Also `postgis_topology` is used.
- Required database objects (materialized views and indexes) are created by scripts in [PRD/database/setup](PRD/database/setup#L1). Key files:
  - [PRD/database/setup/create_school_address_mv.sql](PRD/database/setup/create_school_address_mv.sql#L1-L200)
  - [PRD/database/setup/PostGIS/PostGIS.sql](PRD/database/setup/PostGIS/PostGIS.sql#L1-L80)

Notes:
- Materialized views (`public.school_catchment_addresses`, `public.school_catchment_streets`) are created with `WITH NO DATA` and refreshed `CONCURRENTLY` in the scripts — the DB user needs appropriate privileges to create extensions, indexes, and to refresh materialized views concurrently.

**Python packages** (install via `pip`):
- flask
- flask-login
- psycopg2-binary (or psycopg2 + system `libpq-dev`)
- python-dotenv
- requests (used in tests)
- gunicorn (production WSGI server; optional)
- pytest (for running tests; optional)

Example `pip` install command:

```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install flask flask-login psycopg2-binary python-dotenv requests gunicorn pytest
```

If you prefer a `requirements.txt`, create one with the package names above and run `pip install -r requirements.txt`.

**Database privileges & runtime environment**:
- DB user must have permission to create extensions (or an administrator should run the PostGIS creation script).
- Environment variables (used by `PRD/webapp/app.py`): `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `SECRET_KEY`.
- Test scripts read `.env` if present (python-dotenv).

**Optional / Deployment tooling**:
- **Docker**: Docker and docker-compose for containerized deployment.
- **AWS**: Elastic Beanstalk (quick) or ECR → ECS (Fargate) for container deployments. See [PRD/MD/DEPLOYMENT_GUIDE.md](PRD/MD/DEPLOYMENT_GUIDE.md#L1-L40) for deployment instructions.
- **CI**: GitHub Actions recommended for building images and running tests.

**Quick DB setup summary**:
1. Install PostgreSQL and PostGIS on your host.
2. Create the target database and a privileged user to run the DB setup scripts.
3. Run the PostGIS extension script: `psql -d <db> -f PRD/database/setup/PostGIS/PostGIS.sql` (run as a superuser if needed).
4. Run materialized view scripts in [PRD/database/setup](PRD/database/setup) (they create MVs, indexes and `REFRESH MATERIALIZED VIEW CONCURRENTLY`).

**Where to find scripts**:
- SQL and loader scripts: [PRD/database/setup](PRD/database/setup)
- Flask app: [PRD/webapp/app.py](PRD/webapp/app.py#L1-L40)
- Autocomplete tests: [PRD/webapp/tests/test_school_autocomplete.py](PRD/webapp/tests/test_school_autocomplete.py#L1-L40)

If you want, I can generate a `requirements.txt` and a Dockerfile next — tell me which Python base image and target deployment you prefer.
