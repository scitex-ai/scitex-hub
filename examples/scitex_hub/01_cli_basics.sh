#!/bin/bash
# File: examples/scitex_hub/01_cli_basics.sh
# Demonstrate basic CLI usage

echo "1. Show version:"
scitex-hub --version

echo
echo "2. Show main help:"
scitex-hub --help

echo
echo "3. Show setup help:"
scitex-hub setup --help

echo
echo "4. Show docker subcommands:"
scitex-hub docker --help
