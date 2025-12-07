.PHONY: all install install-dev test test-core test-server test-cli test-harbor \
        lint format run-cli run-server run-demo help clean

# Default target
all: help

######################
# INSTALLATION
######################

# Install all packages in development mode (editable)
install:
	pip install -e source/dataagent-core
	pip install -e source/dataagent-cli
	pip install -e source/dataagent-server
	pip install -e source/dataagent-harbor
	pip install -e source/dataagent-server-demo

# Install with development dependencies
install-dev:
	pip install -e "source/dataagent-core[test,mcp]"
	pip install -e source/dataagent-cli
	pip install -e "source/dataagent-server[dev]"
	pip install -e "source/dataagent-harbor[dev]"
	pip install -e source/dataagent-server-demo

# Reinstall all packages (force reinstall)
reinstall:
	pip install -e source/dataagent-core --force-reinstall --no-deps
	pip install -e source/dataagent-cli --force-reinstall --no-deps
	pip install -e source/dataagent-server --force-reinstall --no-deps
	pip install -e source/dataagent-harbor --force-reinstall --no-deps

######################
# RUNNING
######################

# PYTHONPATH 设置 - 让修改 Core 后只需重启即可生效
PYTHONPATH_DEV = PYTHONPATH=source/dataagent-core:source/dataagent-cli:source/dataagent-server:source/dataagent-harbor:source/dataagent-server-demo:$(PYTHONPATH)

# Reload 目录 - 监控 Core 和 Server 代码变化
RELOAD_DIRS = --reload-dir source/dataagent-core --reload-dir source/dataagent-server

# Run CLI in development mode
run-cli:
	$(PYTHONPATH_DEV) python -m dataagent_cli.main

# Run CLI with specific agent
run-cli-agent:
	$(PYTHONPATH_DEV) python -m dataagent_cli.main --agent $(AGENT)

# Run CLI with auto-approve
run-cli-auto:
	$(PYTHONPATH_DEV) python -m dataagent_cli.main --auto-approve

# Run Server in development mode (auto-reload on Core & Server changes)
run-server:
	@echo "Starting Server with hot-reload (Core & Server changes will auto-reload)..."
	$(PYTHONPATH_DEV) uvicorn dataagent_server.main:app --reload $(RELOAD_DIRS) --host 0.0.0.0 --port 8000

# Run Server on custom port
run-server-port:
	$(PYTHONPATH_DEV) uvicorn dataagent_server.main:app --reload $(RELOAD_DIRS) --host 0.0.0.0 --port $(PORT)

# Run Streamlit Demo
run-demo:
	$(PYTHONPATH_DEV) streamlit run source/dataagent-server-demo/dataagent_server_demo/app.py --server.runOnSave true

# Run Server + Demo together (recommended for development)
run-dev:
	@echo "Starting Server + Demo (Core & Server changes will auto-reload)..."
	@$(PYTHONPATH_DEV) uvicorn dataagent_server.main:app --reload $(RELOAD_DIRS) --host 0.0.0.0 --port 8000 &
	@sleep 2
	@echo "Starting Demo..."
	@$(PYTHONPATH_DEV) streamlit run source/dataagent-server-demo/dataagent_server_demo/app.py --server.runOnSave true

# Show CLI help
cli-help:
	python -m dataagent_cli.main help

# Show Server help
server-help:
	python -c "from dataagent_server.main import app; print('Server endpoints:', [r.path for r in app.routes])"

######################
# TESTING
######################

# Run all tests
test:
	pytest source/dataagent-core/tests source/dataagent-server/tests -v

# Run core tests only
test-core:
	pytest source/dataagent-core/tests -v

# Run server tests only
test-server:
	pytest source/dataagent-server/tests -v

# Run harbor tests only
test-harbor:
	pytest source/dataagent-harbor/tests -v

# Run tests with coverage
test-cov:
	pytest source/dataagent-core/tests --cov=dataagent_core --cov-report=html
	pytest source/dataagent-server/tests --cov=dataagent_server --cov-report=html --cov-append

# Run specific test file
test-file:
	pytest $(FILE) -v

# Run multi-tenant isolation tests
test-isolation:
	@echo "Initializing test users..."
	@python scripts/init_test_users.py --verbose
	@echo ""
	@echo "Running isolation tests..."
	pytest source/dataagent-server/tests/test_multi_tenant -v

# Run isolation tests with report
test-isolation-report:
	@python scripts/init_test_users.py
	./scripts/run_isolation_tests.sh --report

# Quick isolation test (critical tests only)
test-isolation-quick:
	@python scripts/init_test_users.py
	pytest source/dataagent-server/tests/test_multi_tenant -v -m "not slow"

# Reset and reinitialize test users
test-isolation-reset:
	python scripts/init_test_users.py --reset --verbose

######################
# LINTING AND FORMATTING
######################

PYTHON_DIRS = source/dataagent-core/dataagent_core source/dataagent-cli/dataagent_cli \
              source/dataagent-server/dataagent_server source/dataagent-harbor/dataagent_harbor

lint:
	ruff check $(PYTHON_DIRS)

format:
	ruff format $(PYTHON_DIRS)
	ruff check --fix $(PYTHON_DIRS)

# Type checking
typecheck:
	mypy source/dataagent-core/dataagent_core
	mypy source/dataagent-server/dataagent_server

######################
# CLEANUP
######################

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".hypothesis" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage

######################
# HELP
######################

help:
	@echo '===================='
	@echo 'DataAgent Development Commands'
	@echo '===================='
	@echo ''
	@echo '-- INSTALLATION --'
	@echo '  make install          Install all packages in dev mode'
	@echo '  make install-dev      Install with dev dependencies'
	@echo '  make reinstall        Force reinstall all packages'
	@echo ''
	@echo '-- RUNNING --'
	@echo '  make run-cli          Run CLI interactively'
	@echo '  make run-cli-agent AGENT=mybot  Run CLI with specific agent'
	@echo '  make run-cli-auto     Run CLI with auto-approve'
	@echo '  make run-server       Run Server with hot-reload (port 8000)'
	@echo '  make run-server-port PORT=9000  Run Server on custom port'
	@echo '  make run-demo         Run Streamlit demo (with hot-reload)'
	@echo '  make run-dev          Run Server + Demo together (recommended)'
	@echo '  make cli-help         Show CLI help'
	@echo ''
	@echo '-- TESTING --'
	@echo '  make test             Run all tests'
	@echo '  make test-core        Run core tests only'
	@echo '  make test-server      Run server tests only'
	@echo '  make test-harbor      Run harbor tests only'
	@echo '  make test-cov         Run tests with coverage'
	@echo '  make test-file FILE=path/to/test.py  Run specific test'
	@echo ''
	@echo '-- ISOLATION TESTING (Multi-Tenant Security) --'
	@echo '  make test-isolation        Run all isolation tests'
	@echo '  make test-isolation-report Run with HTML report'
	@echo '  make test-isolation-quick  Run critical tests only'
	@echo '  make test-isolation-reset  Reset test users'
	@echo ''
	@echo '-- CODE QUALITY --'
	@echo '  make lint             Run linter'
	@echo '  make format           Format code'
	@echo '  make typecheck        Run type checker'
	@echo ''
	@echo '-- CLEANUP --'
	@echo '  make clean            Remove cache files'
	@echo ''
