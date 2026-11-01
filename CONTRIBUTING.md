# Contributing

`src/advernue/_generated/` is generated from `spec/openapi.json` by `scripts/generate.py` (stdlib only). Do not edit those files by hand; change the generator or the spec and regenerate.

## Regenerate

```bash
cp /path/to/new/openapi.json spec/openapi.json
python scripts/generate.py            # writes src/advernue/_generated/
git diff --stat src/advernue/_generated
```

What it emits: `models.py` (TypedDicts for every component schema plus inline request/response bodies), `sync_api.py` and `async_api.py` (one namespace class per tag, one method per operation; `operationId` is `<tag>.<operation>`, camelCase converted to snake_case). Non-GET operations get `idempotency_key` and `dry_run` arguments.

## Develop

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
ruff check . && mypy && pytest
```

CI runs the same on Python 3.10 to 3.13. Releases: push a tag `v*`; the workflow builds, attests provenance and publishes to PyPI by trusted publishing.
