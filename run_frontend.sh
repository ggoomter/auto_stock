#!/bin/bash

echo "================================================"
echo "  Financial Research Copilot - Frontend UI"
echo "================================================"
echo ""

cd frontend

echo "[1/2] Installing dependencies..."
npm install
echo ""

echo "[2/2] Starting Vite dev server..."
echo "Frontend will be available at: http://localhost:5173"
echo ""
npm run dev
