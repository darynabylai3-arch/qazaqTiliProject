#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 JobHunter запускается на http://localhost:8000"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
