#!/bin/bash

set -e

# start virtual environment
. .venv/bin/activate

# change to the frontend directory
cd ../frontend

# execute `npx json2ts` to generate TypeScript interfaces from the Pydantic models
pydantic2ts --json2ts-cmd 'npx json2ts' --module app.core.sio.models --output src/lib/models.ts
