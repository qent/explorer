# Guidelines for Codex Agents

These instructions apply to all files in this repository.

## Development practices

Follow these clean code principles when contributing:
- Document public classes and functions with concise docstrings.
- Prefer composition over deep inheritance.
- Keep functions short and focused on a single task.

- Target **Python 3.11+** and use modern language features.
- Provide explicit type hints for all function arguments and return values.
- Keep modules small and easy to reason about. Use `pydantic` or dataclasses for structured data.
- Write unit tests for new behaviour in the `tests/` directory using `pytest`.
- Format code with **black** and **isort**.
- Lint with **ruff** and perform static type checking with **mypy** (prefer `--strict`).
- Ensure `pytest`, `ruff`, `black`, `isort` and `mypy` succeed before committing.

## Commit rules

- Use descriptive commit messages written in English.
- Do not amend existing commits or force push.
- Always check `git status` to ensure the working tree is clean before finishing.

## Pull request notes

When creating a pull request, briefly describe what was changed and mention the results of running the test commands.


