# Backend Test Suite

This directory contains comprehensive unit and integration tests for the London Evacuation Planning Tool backend.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared pytest fixtures and configuration
├── fixtures/                   # Test data and configuration files
│   └── test_sources.yml       # Test sources configuration
├── unit/                       # Unit tests
│   ├── core/                   # Core module tests
│   │   ├── test_config.py      # Configuration management tests
│   ├── models/                 # Data model tests
│   │   └── test_schemas.py     # Pydantic schema tests
│   ├── agents/                 # Agent module tests
│   │   ├── test_explainer_agent.py  # RAG explanation agent tests
│   │   └── test_judge_agent.py      # Scenario ranking agent tests
│   ├── services/               # Service module tests
│   │   └── test_storage_service.py  # Storage service tests
│   ├── metrics/                # Metrics system tests
│   │   ├── test_operations.py  # Metrics operations tests
│   │   └── test_builder.py     # Metrics builder tests
│   └── scenarios/              # Scenario system tests
│       └── test_builder.py     # Scenario builder tests
├── api/                        # API endpoint tests
│   └── endpoints/              # Individual endpoint tests
│       ├── test_health.py      # Health check endpoint tests
│       └── test_metrics.py     # Metrics API tests
└── integration/                # Integration tests (placeholder)
```

## Test Categories

### Unit Tests (`tests/unit/`)

Unit tests focus on testing individual components in isolation with mocked dependencies:

- **Core Tests**: Configuration management, settings validation
- **Model Tests**: Pydantic schema validation, data model integrity
- **Agent Tests**: Individual agent behavior, AI client mocking
- **Service Tests**: Business logic, storage operations, data processing
- **Metrics Tests**: Calculation operations, data aggregation
- **Scenario Tests**: Scenario generation, template management

### API Tests (`tests/api/`)

API tests verify HTTP endpoints and request/response handling:

- **Health Endpoints**: System health checks, readiness probes
- **Metrics Endpoints**: Metrics calculation APIs, data retrieval
- **Authentication**: API security and access control (when implemented)

### Integration Tests (`tests/integration/`)

Integration tests verify component interactions and end-to-end workflows:

- **Full Workflow Tests**: Complete evacuation planning workflows
- **Database Integration**: Data persistence and retrieval
- **External Service Integration**: AI services, storage backends

## Test Configuration

### Pytest Configuration (`pytest.ini`)

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v 
    --tb=short
    --strict-markers
    --strict-config
    --disable-warnings
    --cov=.
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=80
asyncio_mode = auto
```

### Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests  
- `@pytest.mark.api`: API endpoint tests
- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.requires_ai`: Tests requiring AI services
- `@pytest.mark.requires_redis`: Tests requiring Redis
- `@pytest.mark.requires_storage`: Tests requiring storage services

## Running Tests

### Using the Test Runner

The recommended way to run tests is using the provided test runner:

```bash
# Run all tests with coverage
./run_tests.py

# Run only unit tests
./run_tests.py --type unit

# Run specific test file
./run_tests.py tests/unit/core/test_config.py

# Run tests with specific markers
./run_tests.py --markers "unit and not slow"

# Run tests in parallel
./run_tests.py --parallel

# Generate HTML coverage report
./run_tests.py --html-report

# Run linting checks
./run_tests.py --lint

# Format code
./run_tests.py --format
```

### Using Pytest Directly

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/api/
pytest -m "unit"
pytest -m "api and not slow"

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/core/test_config.py

# Run specific test method
pytest tests/unit/core/test_config.py::TestSettings::test_default_settings
```

## Test Fixtures

### Shared Fixtures (`conftest.py`)

Common fixtures available to all tests:

- `test_settings`: Test configuration settings
- `temp_storage_dir`: Temporary directory for test storage
- `mock_settings`: Mocked settings for dependency injection
- `client`: FastAPI test client
- `async_client`: Async HTTP test client
- `sample_user_intent`: Sample user intent data
- `sample_timeseries_data`: Sample simulation timeseries data
- `sample_events_data`: Sample simulation events data
- `mock_openai_client`: Mocked OpenAI client
- `mock_anthropic_client`: Mocked Anthropic client

### Custom Fixtures

Individual test modules may define additional fixtures for specific testing needs.

## Test Data

### Test Configuration Files

- `tests/fixtures/test_sources.yml`: Test data sources configuration
- Sample data generators for simulation results, scenarios, and metrics

### Mock Data

Tests use realistic mock data that mirrors production data structures:

- Evacuation scenarios with proper schema validation
- Simulation metrics with realistic value ranges
- User intents with valid preference weights
- Document citations with proper metadata

## Coverage Requirements

- **Minimum Coverage**: 80% overall
- **Target Coverage**: 90%+ for critical components
- **Coverage Reports**: Generated in `htmlcov/` directory

### Coverage Exclusions

The following are excluded from coverage requirements:

- Test files themselves
- Development utilities
- External service integrations (mocked in tests)
- Error handling for system-level failures

## Best Practices

### Test Organization

1. **One test class per module**: `TestClassName` for each module
2. **Descriptive test names**: `test_method_name_expected_behavior`
3. **Setup/teardown**: Use `setup_method`/`teardown_method` for test isolation
4. **Fixtures**: Use fixtures for common test data and mocks

### Test Writing Guidelines

1. **Arrange-Act-Assert**: Clear test structure
2. **Test isolation**: Each test should be independent
3. **Mock external dependencies**: Don't rely on external services
4. **Test edge cases**: Include error conditions and boundary values
5. **Async testing**: Use `pytest-asyncio` for async code

### Mock Strategy

1. **Mock at boundaries**: Mock external services, not internal logic
2. **Realistic mocks**: Mock data should match production data structures
3. **Verify interactions**: Assert that mocks are called correctly
4. **Patch appropriately**: Use `@patch` decorator or context managers

## Continuous Integration

Tests are designed to run in CI environments:

- **No external dependencies**: All external services are mocked
- **Deterministic**: Tests produce consistent results
- **Fast execution**: Unit tests complete quickly
- **Parallel execution**: Tests can run in parallel safely

## Debugging Tests

### Running Individual Tests

```bash
# Run single test with verbose output
pytest -v tests/unit/core/test_config.py::TestSettings::test_default_settings

# Run with debugging output
pytest -s tests/unit/core/test_config.py

# Run with pdb debugger
pytest --pdb tests/unit/core/test_config.py
```

### Common Issues

1. **Import errors**: Ensure PYTHONPATH includes backend directory
2. **Fixture not found**: Check fixture scope and availability
3. **Async test failures**: Ensure `pytest-asyncio` is installed
4. **Mock issues**: Verify mock patch targets and return values

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_*.py` files, `Test*` classes
2. **Add appropriate markers**: Use `@pytest.mark.*` decorators
3. **Update fixtures**: Add new fixtures to `conftest.py` if reusable
4. **Document complex tests**: Add docstrings for complex test logic
5. **Maintain coverage**: Ensure new code is adequately tested

## Dependencies

### Required Packages

- `pytest`: Test framework
- `pytest-asyncio`: Async test support
- `pytest-httpx`: HTTP client testing
- `pytest-mock`: Enhanced mocking capabilities

### Optional Packages

- `pytest-xdist`: Parallel test execution
- `pytest-cov`: Coverage reporting
- `pytest-html`: HTML test reports

Install all test dependencies:

```bash
pip install -e .[dev]
```

## Performance

### Test Execution Times

- **Unit tests**: < 30 seconds total
- **API tests**: < 60 seconds total  
- **Integration tests**: < 120 seconds total
- **Full suite**: < 5 minutes total

### Optimization Tips

1. **Use fixtures**: Avoid repeated setup in tests
2. **Mock expensive operations**: Don't perform actual AI calls or file I/O
3. **Parallel execution**: Use `pytest-xdist` for faster execution
4. **Selective testing**: Run only relevant tests during development
