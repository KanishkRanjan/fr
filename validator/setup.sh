#!/usr/bin/env bash
# One-time setup: fetch + build the native Bliss tool, record its path.
# Requires: git, cc/g++ (Xcode CLT or gcc), make.
set -euo pipefail
cd "$(dirname "$0")/vendor"

[ -d bliss ] || git clone --depth 1 https://github.com/digraphs/bliss

# bliss: plain Makefile build producing the ./bliss CLI.
make -C bliss

cat > paths.json <<EOF
{
  "bliss": "$(pwd)/bliss/bliss"
}
EOF

echo "OK:"
echo "  bliss -> $(pwd)/bliss/bliss"
