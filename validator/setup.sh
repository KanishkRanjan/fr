#!/usr/bin/env bash
# One-time setup: fetch + build the native Bliss and Saucy tools, record their paths.
# Requires: git, cc/g++ (Xcode CLT or gcc), make.
set -euo pipefail
cd "$(dirname "$0")/vendor"

[ -d saucy ] || git clone --depth 1 https://github.com/hrbrmstr/saucy
[ -d bliss ] || git clone --depth 1 https://github.com/digraphs/bliss

# saucy: the upstream repo is an R wrapper; its engine (src/ssaucy.c) is pure C.
# saucy_cli.c is our thin stdin/stdout driver around that engine.
cc -O2 -I saucy/src -o saucy_bin saucy_cli.c saucy/src/ssaucy.c

# bliss: plain Makefile build producing the ./bliss CLI.
make -C bliss

cat > paths.json <<EOF
{
  "bliss": "$(pwd)/bliss/bliss",
  "saucy": "$(pwd)/saucy_bin"
}
EOF

echo "OK:"
echo "  bliss -> $(pwd)/bliss/bliss"
echo "  saucy -> $(pwd)/saucy_bin"
