#!/bin/bash
# Test runner for Glasswatch backend tests
# Runs all unit and integration tests with pytest

set -e

cd "$(dirname "$0")/.."

echo "======================================"
echo "  Glasswatch Backend Test Suite"
echo "======================================"
echo ""

# Check if pytest is available
if ! python -m pytest --version >/dev/null 2>&1; then
    echo "ERROR: pytest not found. Install with: pip install pytest pytest-asyncio httpx"
    exit 1
fi

echo "Running tests..."
echo ""

# Run pytest with:
# -v: verbose output
# --tb=short: shorter traceback format
# -x: stop on first failure
# --timeout=30: timeout for individual tests
python -m pytest tests/ -v --tb=short -x --timeout=30 2>&1

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "======================================"
    echo "  ✓ All tests passed!"
    echo "======================================"
else
    echo "======================================"
    echo "  ✗ Tests failed with exit code $exit_code"
    echo "======================================"
fi

exit $exit_code
