# Contributing to SeptaStack

Thank you for your interest in contributing!

## Getting Started

```bash
git clone <repo-url> && cd septastack
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
```

## Running Tests

```bash
python -m pytest tests/ -v
```

All 576 tests must pass before submitting changes.

## Project Structure

Each compiler stage lives in its own module under `septa/`. Tests live in `tests/` at the project root.

See [docs/architecture.md](docs/architecture.md) for how the pipeline works.

## Guidelines

- Keep changes focused — one PR per feature or fix
- Add tests for new functionality
- Follow existing code style (PEP 8, type hints)
- No external dependencies in the core package
- Run the full test suite before submitting

## Reporting Issues

Open a GitHub issue with:
- What you expected
- What actually happened
- Steps to reproduce
- Python version and OS
