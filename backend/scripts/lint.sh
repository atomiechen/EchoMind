#!/usr/bin/env bash

set -e
set -x

ruff check app
ruff format app --check --diff
