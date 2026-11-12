#!/bin/sh
set -eu
app_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec uv run --project "$app_dir" --locked python "$app_dir/desktop_app.py" "$@"
