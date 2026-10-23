# Django backend

## Status on `main`

This directory is currently a placeholder on `main`. The Django project, analytics app, migrations, importer, and REST API described in [the architecture](../docs/architecture.md) are part of the current development work but have not yet been merged into this branch. Do not expect `manage.py` or the documented API endpoints to be runnable from `main` until that implementation is integrated.

## Intended responsibilities

- Django settings and URL configuration.
- Domain models: `Student`, `Course`, `Enrollment`, `Assessment`, and `Interaction`.
- Database migrations and admin registration.
- Controlled OULAD import and validation.
- DRF endpoints and aggregated analytics.
- Automated model, import, analytics, and API tests.

See [architecture and implementation decisions](../docs/architecture.md) for model grain, data-quality decisions, known trade-offs, current development checkpoint, and next milestones.
