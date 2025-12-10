# Converted RustKmer Python Tests

This directory contains tests converted from the root directory `test*.py` files to use proper pytest infrastructure.

## Setup

1. Activate the virtual environment:
```bash
source .venv/bin/activate
```

2. Build the RustKmer Python bindings:
```bash
cd python && maturin develop --release && cd ..
```

## Running Tests

### Run all converted tests:
```bash
pytest tests/converted/ -v
```

### Run specific test file:
```bash
pytest tests/converted/test_fuzzy_query.py -v
```

### Run with markers:
```bash
# Run only converted tests
pytest tests/converted/ -m "converted" -v

# Run only integration tests
pytest tests/converted/ -m "integration" -v

# Run only unit tests
pytest tests/converted/ -m "unit" -v
```

### Using the test runner:
```bash
tests/converted/run_tests.py
```

## Test Categories

- **Unit tests**: Test individual components and methods
- **Integration tests**: Test multiple components working together
- **Converted tests**: Originally from root directory, now using pytest

## Current Status

- ✅ Virtual environment created with Python 3.13.5
- ✅ Pytest infrastructure set up
- ✅ `test_fuzzy_query.py` converted (3/5 tests passing)
- ⏳ Other test files pending conversion

## Known Issues

1. Some API methods in the Python wrapper have different signatures than expected
2. `DatabaseStats` initialization has unexpected parameters
3. `QueryResult` class may not be properly exposed

## Next Steps

1. Fix remaining API compatibility issues
2. Convert remaining root directory test files
3. Add proper fixtures for common test setup
4. Improve test coverage