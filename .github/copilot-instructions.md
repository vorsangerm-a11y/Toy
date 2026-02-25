# GitHub Copilot Instructions — Toy (Python Project)

## Architecture Overview

- **Stack**: Python 3.12, src/ layout
- **Governance**: Mault enforced — see `docs/mault.yaml`
- **Testing**: pytest with Pure Core Pattern (unit + integration)

## File Structure Rules

Place files in the correct directory — Mault will flag violations:

| File Pattern       | Location              |
|-------------------|----------------------|
| `*_service.py`    | `src/services/`      |
| `*_repository.py` | `src/repositories/`  |
| `*_model.py`      | `src/models/`        |
| `*_util*.py`      | `src/utils/`         |
| `test_*.py`       | `tests/unit/` or `tests/integration/` |

## Naming Rules

- Files: `snake_case`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE`

## Code Standards

1. **No `print()`** in `src/` — use `logging.getLogger(__name__)`
2. **No bare `except:`** — always specify exception type
3. **No wildcard imports** — use explicit imports
4. **No `# type: ignore`** — fix the type error
5. **No `breakpoint()` or `pdb`** before committing

## Testing Standards

- Unit tests: pure functions, no I/O, in `tests/unit/`
- Integration tests: real I/O, in `tests/integration/`
- Mock Tax: unit test must be ≤ 2x source file size
- Coverage: 80% minimum on new files

## Deprecated Libraries

Never import: `optparse`, `imp`, `urllib2`, `mock`, `nose`, `distutils`
Never call: `os.system()`, `os.popen()`, `hashlib.md5()`, `random.random()` (for security)
