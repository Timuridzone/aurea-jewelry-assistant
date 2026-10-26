# Verification record

Publication preparation: 26 October 2026.

## Automated checks

- Python 3.12, existing local virtual environment, exact versions in `requirements.lock.txt`.
- `python -m pytest -q`: **16 passed**, one upstream Starlette deprecation warning about its HTTPX test transport.
- Tests use temporary SQLite databases; recommendation constraints, fallback preference extraction, ticket lifecycle, persistence and reminder behavior are covered.
- A GitHub Actions workflow is supplied for Python 3.12. Remote CI has not yet been run; a fresh network installation has not been verified in this pass.
- `python scripts/audit_publication.py` checks the tracked publication files for common credential patterns, local home paths and accidentally included runtime data. It is a focused heuristic check, not a guarantee that all secrets or security defects have been detected.

## Manual browser checks

Ran a separate local instance against a new fictional SQLite database, with optional model configuration disabled. The user's existing database was not used for screenshots or modified by these interactions.

- Sent a Spanish silver/minimalist necklace request with a €150 budget; received Collar Marea at €99.
- Requested human assistance; ticket #7 was created/reused and the assistant paused.
- Opened the ticket in the inbox, assigned Lucía Martín and changed status to In Progress.
- Saved a fictional private note and confirmed the note count increased.
- Sent a staff reply; the ticket moved to Waiting for Customer and the reply appeared in the customer simulator.
- Inspected the catalog and reminder configuration pages.
- Inspected the initial mobile dashboard at 320px and the desktop workflow at 1440px. Screenshots in the gallery are full-page desktop captures.

The existing automated tests additionally check that customer responses do not expose staff notes and that new customer messages reopen/reactivate tickets. No live LLM, real WhatsApp, real CRM, payment, inventory or retailer system was exercised.

## Publication boundary

Only application source, tests, placeholder environment documentation, dependency files, reference schema, launcher, documentation, audit script, workflow and six fresh fictional screenshots are selected. Existing databases, database sidecars, virtual environments, caches, the older unverified screenshot and unrelated project/reference files are excluded. A new Git history avoids copying any prior local data or credentials.

The author approved public publication and the MIT License on 26 October 2026.
