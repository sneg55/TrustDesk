# Code Style

## Python
- ruff for linting and formatting
- Line length: 120
- Type hints on all public functions and methods
- `from __future__ import annotations` in every file
- Imports: stdlib → third-party → local, enforced by ruff isort

## Naming
- Files: snake_case always
- Classes: PascalCase
- Functions/methods: snake_case
- Constants: SCREAMING_SNAKE_CASE
- Booleans: is_/has_ prefix
- Private: single underscore prefix

## File Size
- Target: under 200 lines
- Warning: 200-300 lines (hook warns)
- Blocked: over 300 lines (hook blocks write)
- Split by concern: types.py, constants.py, separate implementation files

## Patterns
- No magic strings — use constants
- No raw os.environ — use core/config.py
- Comments explain WHY, never WHAT
- Use `from __future__ import annotations` for forward refs
