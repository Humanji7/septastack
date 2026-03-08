.PHONY: install test run-examples clean

install:
	python -m venv .venv
	.venv/bin/pip install -e .
	.venv/bin/pip install pytest

test:
	python -m pytest tests/ -v

test-quick:
	python -m pytest tests/ -q

run-examples:
	@echo "=== hello ===" && septa run examples/hello.septa
	@echo "=== add ===" && septa run examples/add.septa
	@echo "=== if_else ===" && septa run examples/if_else.septa
	@echo "=== while_loop ===" && septa run examples/while_loop.septa
	@echo "=== memory ===" && septa run examples/memory.septa
	@echo "=== functions ===" && septa run examples/functions.septa

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/
