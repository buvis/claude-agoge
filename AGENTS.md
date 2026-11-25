# agoge

## Commands

- All checks: `dev/bin/release-checks`
- Format before each commit that touches Python: `uvx ruff format skills/run-agoge/scripts`, then `uvx ruff check --fix skills/run-agoge/scripts`. `dev/bin/release-checks` and CI fail on an unformatted file.
