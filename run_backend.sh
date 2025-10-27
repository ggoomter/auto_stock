#!/bin/bash

echo "================================================"
echo "  Financial Research Copilot - Backend Server"
echo "================================================"
echo ""

cd backend

echo "[1/2] Installing dependencies..."
pip install -r requirements.txt
echo ""

echo "[2/2] Starting FastAPI server..."
echo "Backend will be available at: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
