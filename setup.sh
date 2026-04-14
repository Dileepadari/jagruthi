#!/bin/bash
set -e
echo "=== Jagruthi Setup ==="
 
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv portaudio19-dev \
    ffmpeg git espeak-ng libespeak-ng-dev \
    libasound2-dev libsndfile1-dev
 
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
 
# Install Ollama for offline fallback
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b &
 
# Download Piper and voices
bash scripts/download_models.sh
 
# Set .env
if [ ! -f .env ] || grep -q "your_groq_api_key_here" .env; then
  echo ""
  read -p "Enter your Groq API key (get free at console.groq.com): " key
  echo "GROQ_API_KEY=$key" > .env
fi
 
# Systemd service
sudo cp jagruthi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable jagruthi
echo ""
echo "=== Setup complete. Run: source venv/bin/activate && python3 main.py ==="
