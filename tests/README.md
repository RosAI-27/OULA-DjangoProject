# Tests

## Current status

The Phase 6 validation checkpoint passed:

- `python backend/manage.py check` — no system-check issues.
- `python backend/manage.py test analytics` — 5 tests passed at that checkpoint.

Subsequent phases added tests for dashboard statistics, risk scoring and ranking, cutoff-based exclusions, retrospective validation, and agent-request validation. Run `python manage.py test analytics` from `backend/` to execute the current suite. Passing tests do not replace source-to-database reconciliation or methodological review of the analytics.

## Test principles

- Use small synthetic fixtures rather than committing real student-level records.
- Assert expected results, not merely that endpoints return HTTP 200.
- Cover model constraints and relationships, import behaviour, analytics calculations, filters, pagination, and edge cases as the application evolves.
- Keep test data deterministic and independent of the local production-sized OULAD database.
