#!/bin/bash
set -e

VOICES_DIR="tts/voices"
BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main"

mkdir -p "$VOICES_DIR"

echo "=== Installing Piper TTS ==="
if ! pip show piper-tts > /dev/null 2>&1; then
  pip install piper-tts || pip install piper-tts --break-system-packages
else
  echo "Piper TTS already installed."
fi

echo "=== Downloading Piper Voices ==="

download_voice() {
  local path="$1"
  local name=$(basename "$path")   #  only filename

  local model_file="$VOICES_DIR/${name}.onnx"
  local config_file="$VOICES_DIR/${name}.onnx.json"

  if [ -f "$model_file" ] && [ -f "$config_file" ]; then
    echo "[ok] $name already exists"
    return 0
  fi

  echo "⬇ Downloading $name..."

  if curl -fL -o "$model_file" "$BASE_URL/$path.onnx" &&
     curl -fL -o "$config_file" "$BASE_URL/$path.onnx.json"; then
    echo "[ok] $name downloaded"
  else
    echo "[fail] Failed to download $name"
    rm -f "$model_file" "$config_file"
    return 1
  fi
}

# Voices
download_voice "en/en_US/lessac/medium/en_US-lessac-medium"
download_voice "hi/hi_IN/priyamvada/medium/hi_IN-priyamvada-medium"

# Telugu (optional)
download_voice "te/te_IN/padmavathi/medium/te_IN-padmavathi-medium" || \
  echo "[warn] Telugu voice not available - using fallback"

echo "=== Voices Ready ==="
ls -lh "$VOICES_DIR"
