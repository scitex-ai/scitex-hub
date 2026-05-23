#!/bin/bash
# File: examples/scitex_hub/01_cli_basics.sh
# Demonstrate basic CLI usage

echo "1. Show version:"
scitex-cloud --version

echo
echo "2. Show main help:"
scitex-cloud --help

echo
echo "3. Show setup help:"
scitex-cloud setup --help

echo
echo "4. Show docker subcommands:"
scitex-cloud docker --help
