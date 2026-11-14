# Factory Site — Backend (Django API)

Django 5.2 LTS + Django REST Framework backend for the Persian RTL 3D printing / CNC factory site: JWT auth, showcase (Thingiverse-like), shop, custom-order workflow, quotes, orders and ZarinPal payments.

**This directory is its own git repository**, hosted separately from the frontend repo. Clone it anywhere; it does not depend on the parent folder. Only the deployment glue (`docker-compose.yml`, `nginx.conf`, `.env.example`) lives outside — see the workspace README's deployment section.

## Stack

- Python 3.12, Django 5.2 LTS (security support until April 2028), DRF 3.18, SimpleJWT 5.5, django-cors-headers 4.9
- PostgreSQL 16 (psycopg 3.3), Pillow 13, requests 2.34, jdatetime 6.1
- Gunicorn 27 in production

> The original roadmap pinned Django 4.2, which reached end of extended support on April 30, 2026. All pins were modernized past the roadmap — treat roadmap versions as minimums, not exact pins.

## Layout

| Path | Purpose |
|---|---|
| `config/` | settings, urls, wsgi, unified JSON error handler, `.env` loader |
| `accounts/` | email-based custom user, register/login/refresh/logout/me |
| `catalog/` | processes, materials, categories, tags, showcase items/files/images, products, likes, collections, comments, makes, download logs |
| `orders/` | custom requests + files + messages, quotes, orders |
| `payments/` | Payment model, ZarinPal v4 service, pay + callback views |
| `content/` | blog posts, singleton SiteSetting, contact messages |
| `catalog/management/commands/seed_factory.py` | seeds processes/materials/categories/tags/showcase/products |
| `content/management/commands/seed_content.py` | seeds SiteSetting + Persian blog posts |

## Local development

Requires Python 3.12 and a running PostgreSQL 16.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env         # then fill in values (or create backend/.env manually)
python manage.py migrate
python manage.py seed_factory     # idempotent
python manage.py seed_content     # idempotent
python manage.py createsuperuser  # login uses email
python manage.py runserver 8000
```

The API is at `http://localhost:8000/api/`, admin at `/admin/`.
Settings load `backend/.env` automatically (existing environment variables always win).

## Environment variables

All secrets come from the environment; startup **fails** if `DJANGO_SECRET_KEY` is missing (or `DATABASE_URL` when `DEBUG=False`).

| Variable | Required | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | ✅ | no hardcoded fallback |
| `DJANGO_DEBUG` | – | default `False`; sqlite fallback exists only while `True` |
| `DJANGO_ALLOWED_HOSTS` | ✅ (prod) | comma-separated |
| `DATABASE_URL` | ✅ (prod) | `postgres://user:pass@host:5432/db` |
| `MEDIA_ROOT` | – | default `./media`; compose sets `/data/media` |
| `FRONTEND_URL` | – | default `http://localhost:5173`; used for payment-result redirects |
| `SITE_DOMAIN` | – | e.g. `your-domain.com` |
| `CORS_ALLOWED_ORIGINS` | – | comma-separated, read from env only |
| `JWT_ACCESS_TOKEN_MINUTES` | – | default `30` |
| `JWT_REFRESH_TOKEN_DAYS` | – | default `7` |
| `ZARINPAL_MERCHANT_ID` | ✅ (payments) | keep out of logs |
| `ZARINPAL_BASE_URL` | – | production `https://payment.zarinpal.com`; sandbox `https://sandbox.zarinpal.com` |
| `ZARINPAL_CALLBACK_URL` | – | default `<FRONTEND_URL>/api/payments/zarinpal/callback`; must point at the Django verification view |
| `CONTACT_EMAIL` | – | also used as `DEFAULT_FROM_EMAIL` |
| `EMAIL_HOST`, `EMAIL_PORT` | – | default port `587` |

## Tests

```bash
python manage.py test    # 65 tests
```

The suite creates a `test_<DBNAME>` database on the same Postgres server, so Postgres must be running and your DB user needs `createdb` rights.

## API overview

Base `/api/`, JSON only (multipart for uploads), auth via `Authorization: Bearer <access>`.
Errors are always `{"detail": "<Persian message>", "code": "<machine_code>"}` (e.g. `file_too_large`, `quote_expired`).

- `auth/register`, `auth/login`, `auth/refresh`, `auth/me`, `auth/logout`
- `site-setting`, `catalog/processes`, `catalog/materials?process=`, `catalog/categories`
- `showcase` (filters `q/category/tag/process/material`, sort `popular|newest|most_makes`, page size 12), `showcase/{slug}`, `…/like`, `…/save`, `…/comments`, `…/makes`, `…/download[?file_id=]` (no `file_id` → zip of all files, ≤200 MB)
- `collections`, `collections/{id}`
- `products`, `products/{slug}`
- `blog`, `blog/{slug}` (page size 10), `contact`
- `custom-requests` (multipart, ≤5 files, ≤100 MB each, types STL/3MF/OBJ/STEP/STP/IGES/IGS/DXF/JPG/PNG), `custom-requests/{id}`, `…/messages`, `…/accept-quote` (transactional; exactly one order per quote, second accept → 409), `…/reject-quote`
- `orders`, `orders/{id}`, `orders/{id}/pay` → ZarinPal StartPay URL, `payments/zarinpal/callback` (server-side verify; code 100/101 idempotent)

Objects belonging to another user return **404**, never 403.

## File privacy

Customer uploads live under `MEDIA_ROOT/requests/<id>/` and are served **only** through authenticated Django views — never a direct `/media/requests/...` URL (the production nginx config returns 404 for that path). Showcase files go only through the download endpoint.

## Docker

`Dockerfile` (python:3.12-slim) runs Gunicorn as a non-root user on port 8000. It is used by the `web` service in the workspace `docker-compose.yml`; migrations, static files and seeds run automatically on container boot.
