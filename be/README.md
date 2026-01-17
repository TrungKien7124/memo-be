## MEMO Backend Base

Base Django setup for the MEMO platform (Modular Monolith) with DRF, Channels, Celery, PostgreSQL, and Redis hooks. Business logic is intentionally minimal so you can iterate on use cases later.

### Stack
- Django 4.2 + Django REST Framework
- Channels (websocket ready via ASGI)
- Celery + Redis (broker/result)
- PostgreSQL (default) with SQLite fallback for quick local dev

### Quick start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env  # update secrets and connection strings
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### Background workers
- Celery worker: `celery -A memo_backend worker -l info`
- Celery beat (scheduled tasks): `celery -A memo_backend beat -l info`
- ASGI server (optional): `daphne -b 0.0.0.0 -p 8001 memo_backend.asgi:application`

### Environment variables
Key settings are read from `.env` (loaded via `python-dotenv`):
- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `CORS_ALLOW_ALL_ORIGINS`, `CORS_ALLOWED_ORIGINS`
If `POSTGRES_DB` is unset, SQLite is used for local dev.

### Auth model
- Using Django auth with a custom user model (`AUTH_USER_MODEL = app_server.User`).

### App layout
- Django apps:
  - `apps/app_server/` (IAM, CMS, LMS, NFS, SOC, GMS, NTS, ADM)
  - `apps/srs/` (SRS + RSE)
  - `apps/ai/` (ACS + SPS)
- Odoo-like layering in each app:
  - `controllers/{base,implemented,extended}`
  - `models/{base,implemented,extended}`
  - `serializers/{base,implemented,extended}`
  - `normalizers/{base,implemented,extended}`
  - `validators/{base,implemented,extended}` (app_server only, shared base)
  - `routes/{base,implemented,extended}`
  - `pagination/base`, `exceptions/base` (app_server only, shared base)
- Naming convention: `<domain>_<entity>_<layer>.py`
  - Example: `iam_user_controller.py`, `cms_course_serializer.py`, `srs_card_srs_state_model.py`.

### Health checks
- `GET /health/` – project-level ping
- `GET /api/<domain>/health/` – per-domain endpoints (iam/cms/lms/nfs/srs/rse/acs/sps/soc/gms/nts/adm)

### Seed demo data
```bash
python manage.py seed_demo
```

### Next steps
- Implement domain-specific service/usecase logic.
- Add auth (JWT/Session) + permissions per role.
- Wire websocket consumers in `memo_backend/routing.py` and app-level `consumers.py`.
