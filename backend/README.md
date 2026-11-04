# Django backend

The Django project and analytics application are implemented under this directory.

The backend includes:
- Django settings and URL configuration.
- The analytics application with the `Student`, `Course`, `Enrollment`, `Assessment`, and `Interaction` models.
- Database migrations and admin registration.
- Controlled OULAD import and validation.
- Django REST Framework serializers, filters, pagination, and endpoints.
- Aggregated course-level engagement and success-rate analytics.
- Automated tests for the analytics application.

See [architecture and implementation decisions](../docs/architecture.md) for model grain, data-quality decisions, API routes, validation evidence, and the completed risk-indicator, dashboard, and agent work.
