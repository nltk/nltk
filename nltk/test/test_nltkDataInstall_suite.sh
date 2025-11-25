# ...existing code...
#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./test_nltkDataInstall_suite.sh            # run tests (no coverage)
#   ./test_nltkDataInstall_suite.sh --coverage # run tests with coverage
#   ./test_nltkDataInstall_suite.sh --coverage --install-deps
#     (will attempt to install pytest-cov automatically)
#
# Script runs pytest for the selected test files and writes combined coverage
# reports to coverage.xml and coverage_html/ when --coverage is used.

cd "$(dirname "$0")" || exit 1

files=("test_new_punkt_install.py" "test_data_clear_box.py" "test_pip_data_loading.py" "test_find.py")

# Parse flags
COVERAGE=0
INSTALL_DEPS=0
for arg in "$@"; do
  case "$arg" in
    --coverage) COVERAGE=1 ;;
    --install-deps) INSTALL_DEPS=1 ;;
    *) ;;
  esac
done

echo "Selected test files: ${files[*]}"

# Collect the files that actually exist
selected=()
for f in "${files[@]}"; do
  if [ -f "$f" ]; then
    echo "==> Will run tests in: $f"
    selected+=("$f")
  else
    echo "==> Skipping missing file: $f"
  fi
done

if [ "${#selected[@]}" -eq 0 ]; then
  echo "No test files found to run."
  exit 0
fi

if [ "$COVERAGE" -eq 1 ]; then
  # Ensure pytest-cov available, optionally install it
  if ! python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('pytest_cov') else 1)"; then
    if [ "$INSTALL_DEPS" -eq 1 ]; then
      echo "pytest-cov not found. Attempting to install..."
      python -m pip install --upgrade pytest-cov coverage || {
        echo "Automatic install failed. Install pytest-cov manually: python -m pip install pytest-cov coverage"
        exit 1
      }
    else
      echo "pytest-cov not installed. Run with --install-deps or install: python -m pip install pytest-cov coverage"
      exit 1
    fi
  fi

  echo "Running pytest with coverage for package 'nltk'..."
  # Run pytest once for all selected files so coverage is combined
  python -m pytest -q --cov=nltk --cov-report=term-missing --cov-report=xml:coverage.xml --cov-report=html:coverage_html "${selected[@]}"
  echo "Coverage summary written to coverage.xml"
  echo "HTML report written to coverage_html/index.html"
  exit $?
else
  # Run pytest per-file for clearer per-file output
  for f in "${selected[@]}"; do
    echo "==> Running tests in: $f"
    python -m pytest -q "$f" || exit $?
  done
fi
# ...existing code...