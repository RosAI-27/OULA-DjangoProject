# Tests

## Current status

The repository's `main` branch currently contains test guidance, but the Django implementation and its automated tests have not yet been integrated. The development checkpoint previously ran `python backend/manage.py test analytics` and Django reported zero tests; this is a gap, not evidence that the app is adequately tested.

## Priorities when backend code is integrated

- Model constraints and relationships.
- Data validation and import behavior, including reruns/failure handling.
- Assessment-to-enrolment module/presentation consistency.
- Interaction aggregation and click-total correctness.
- Analytics calculations, including success-rate denominator and withdrawal reporting.
- API filters, pagination, empty/null cases, response schemas, and permissions if applicable.

Use small synthetic fixtures rather than committing real student-level records. Tests should assert expected results, not merely that endpoints return HTTP 200.
