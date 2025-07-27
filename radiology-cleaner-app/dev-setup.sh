#!/bin/zsh

# Radiology Cleaner App - Local Development Setup Script
# This script sets up and starts both backend and frontend for local development

set -e  # Exit on any error

echo "🚀 Setting up Radiology Cleaner App for local development..."

# Check if we're in the right directory
if [[ ! -f "app.js" ]] || [[ ! -d "backend" ]]; then
    echo "❌ Error: Please run this script from the radiology-cleaner-app root directory"
    exit 1
fi

# Check if virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]]; then
    # Check if .venv exists, create if it doesn't
    if [[ ! -d ".venv" ]]; then
        echo "📦 Creating Python virtual environment..."
        python3 -m venv .venv
    fi
    
    # Activate virtual environment
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "🔧 Virtual environment already active: $VIRTUAL_ENV"
fi

# Install Python dependencies
echo "📥 Installing Python dependencies..."
cd backend

# Check if requirements.txt exists
if [[ -f "requirements.txt" ]]; then
    echo "   Installing from requirements.txt..."
    pip install -r requirements.txt
else
    echo "   Installing core dependencies..."
    pip install flask flask-cors pyyaml numpy faiss-cpu requests fuzzywuzzy python-levenshtein transformers torch sentence-transformers
    
    # Generate requirements.txt for future use
    echo "   Generating requirements.txt..."
    pip freeze > requirements.txt
    echo "   ✅ Generated requirements.txt"
fi

# Go back to root
cd ..

# Start backend server in background
echo "🖥️  Starting backend server on http://localhost:10000..."
cd backend
nohup python3 app.py > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 8

# Test backend connectivity
echo "🔍 Testing backend connectivity..."
HEALTH_RESPONSE=$(curl -s http://localhost:10000/health 2>/dev/null)
if [[ $? -eq 0 ]] && [[ -n "$HEALTH_RESPONSE" ]]; then
    echo "   ✅ Backend is running (PID: $BACKEND_PID)"
    echo "   Health check: $HEALTH_RESPONSE"
else
    echo "   ⚠️  Backend may still be initializing... checking process..."
    if ps -p $BACKEND_PID > /dev/null; then
        echo "   ✅ Backend process is running (PID: $BACKEND_PID)"
        echo "   Recent logs:"
        tail -5 backend.log 2>/dev/null || echo "   No log file found"
    else
        echo "   ❌ Backend process died - check backend.log for errors"
        echo "   Backend log:"
        cat backend.log 2>/dev/null || echo "   No log file found"
        exit 1
    fi
fi

# Start frontend server
echo "🌐 Starting frontend server on http://localhost:8000..."
echo "   Frontend will auto-detect localhost and connect to backend"
echo ""
echo "📋 Setup Complete!"
echo "   Backend:  http://localhost:10000"
echo "   Frontend: http://localhost:8000"
echo "   Mode:     LOCAL (auto-detected)"
echo ""
echo "🎯 Open http://localhost:8000 in your browser to use the app"
echo ""
echo "To stop servers:"
echo "   Press Ctrl+C to stop frontend"
echo "   Backend PID: $BACKEND_PID (kill $BACKEND_PID to stop)"
echo ""

# Start frontend server (this will block)
python3 -m http.server 8000

# Cleanup when frontend server is stopped
echo ""
echo "🧹 Cleaning up..."
kill $BACKEND_PID 2>/dev/null || true
echo "✅ Servers stopped"