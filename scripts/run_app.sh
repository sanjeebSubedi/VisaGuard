#!/bin/bash
# Run the VisaGuard Streamlit application

set -e

echo "🛡️ Starting VisaGuard..."
echo ""

# Check for required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set. Some features may be limited."
fi

if [ -z "$LLAMA_CLOUD_API_KEY" ]; then
    echo "⚠️  Warning: LLAMA_CLOUD_API_KEY not set. PDF parsing will use fallback."
fi

echo ""
echo "Starting Streamlit server..."
echo "Open http://localhost:8501 in your browser"
echo ""

# Run Streamlit
uv run streamlit run app/frontend/streamlit_app.py --server.port 8501 --server.headless true
