#!/bin/bash

set -e

# start virtual environment
. .venv/bin/activate
# generate openapi.json
python -c "import app.main; import json; print(json.dumps(app.main.app.openapi(), ensure_ascii=False, indent=2))" > ../frontend/openapi.json

# generate frontend client code
cd ../frontend
npm run gen-client
