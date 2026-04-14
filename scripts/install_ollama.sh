#!/bin/bash
set -e
echo "Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
echo "Pulling llama3.2:3b (offline fallback model)..."
ollama pull llama3.2:3b
echo "Done."