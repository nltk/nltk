#!/usr/bin/env bash
set -euo pipefail

# Run pytest only for new_punkt and data_clear_box test files
cd "$(dirname "$0")"

files=("test_new_punkt_install.py" "test_data_clear_box.py")

echo "Running pytest for files: ${files[*]}"
for f in "${files[@]}"; do
  if [ -f "$f" ]; then
    echo "==> Running tests in: $f"
    python -m pytest -q "$f"
  else
    echo "==> Skipping missing file: $f"
  fi
done