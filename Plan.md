# Jagruthi - Campus Conversational AI
## Complete System Design, Architecture & Build Plan

---

## 1. What Jagruthi Actually Is

A **campus-deployed, voice-first conversational AI kiosk** running on Raspberry Pi that:
- Answers institutional queries via RAG (no hallucination, grounded answers)
- Adapts responses by role: student / faculty / staff
- Provides emotional support as a personal companion
- Speaks naturally in Telugu, Hindi, and English
- Works **entirely free**, mostly offline after setup
- Randomly checks in on users (like a friend texting you)

---

## 2. Hardware Requirements

| Component | Spec | Notes |
|---|---|---|
| Raspberry Pi | 4B (4GB min) or 5 (8GB preferred) | RPi 5 cuts inference time ~3× |
| Microphone | USB Mic or ReSpeaker HAT | ReSpeaker 2-Mic HAT is ideal for noise cancellation |
| Speaker | 3.5mm or USB speaker | Minimum 3W |
| Storage | 64GB+ microSD (A2 class) or SSD via USB | SSD strongly recommended |
| Display (optional) | 7" HDMI touchscreen | For visual feedback |
| Power | 5V 3A USB-C (RPi4) / 5V 5A (RPi5) | Stable supply is critical |
| Enclosure | 3D printed kiosk shell | You can print this - nice touch |

---

## 3. Complete Tech Stack (100% Free)

### 3.1 Wake Word Detection
**Tool:** `openWakeWord` (https://github.com/dscripka/openWakeWord)
- Fully free, runs on RPi
- Custom wake word training supported ("Hey Jagruthi")
- ~5ms detection latency

### 3.2 Speech-to-Text (STT)
**Tool:** `faster-whisper` (CTranslate2 optimized Whisper)
- **Model:** `small` (244MB) for RPi 4 or `medium` for RPi 5
- **Why not base?** Base has poor Telugu/Hindi accuracy
- **Why not large?** Too slow on RPi
- Multilingual detection: auto or forced
- ~2-4 sec transcription on RPi 4 for 5s audio

### 3.3 Language Model (LLM)
**Two strategies - use both:**

| Strategy | Tool | When |
|---|---|---|
| Online (primary) | **Groq API** - free tier, Llama 3.1 70B | When internet available |
| Offline fallback | **Ollama** with `llama3.2:3b` or `phi3:mini` | When offline |

Groq free tier: 14,400 requests/day, 6000 tokens/min - more than enough for a campus kiosk.

### 3.4 Embeddings
**Tool:** `sentence-transformers` - `BAAI/bge-small-en-v1.5`
- 33MB, runs entirely local
- Good multilingual support
- ~50ms per embedding on RPi 4

### 3.5 Vector Database
**Tool:** `ChromaDB` (local, persistent mode)
- Zero cost, embedded into the Python process
- Persists to disk - no server needed
- Handles 100K+ document chunks fine

### 3.6 Text-to-Speech (TTS)
**Tool:** `Piper TTS` (https://github.com/rhasspy/piper)
- Designed specifically for Raspberry Pi
- Sub-100ms inference
- Free voices for: English (en_US, en_GB), Hindi (hi_IN), Telugu (te_IN)
- Natural prosody - not robotic

**Backup for richer multilingual:** `Coqui XTTS v2` (if RPi 5 + SSD)
- More natural but heavier (~1.8GB model)

### 3.7 Orchestration
**Tool:** `LangChain` + `LangGraph`
- RAG chain
- Conversation memory (windowed)
- Role-based routing
- Emotional state detection chain

### 3.8 Scheduler (Random Check-ins)
**Tool:** `APScheduler` (Python)
- Cron-like or interval-based random call triggers
- Configurable per-role

---

## 4. System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        RASPBERRY PI                              │
│                                                                  │
│  ┌────────────┐    ┌──────────────┐    ┌────────────────────┐   │
│  │  Mic Input │───▶│ openWakeWord │───▶│  Audio Capture     │   │
│  └────────────┘    └──────────────┘    │  (sounddevice)     │   │
│                                        └────────┬───────────┘   │
│                                                 │               │
│                                        ┌────────▼───────────┐   │
│                                        │  faster-whisper    │   │
│                                        │  (STT + lang det.) │   │
│                                        └────────┬───────────┘   │
│                                                 │               │
│                                        ┌────────▼───────────┐   │
│                                        │  Intent Router     │   │
│                                        │  (LangChain)       │   │
│                                        └──┬──────┬──────┬───┘   │
│                                           │      │      │       │
│                               ┌───────────┘      │      └────┐  │
│                          ┌────▼─────┐  ┌─────────▼──┐  ┌────▼┐ │
│                          │RAG Chain │  │ Emotional  │  │Role │ │
│                          │ChromaDB  │  │ Support    │  │Gate │ │
│                          │+Groq LLM │  │ Chain      │  │     │ │
│                          └────┬─────┘  └─────┬──────┘  └──┬──┘ │
│                               │              │             │    │
│                               └──────┬───────┘─────────────┘    │
│                                      │                          │
│                              ┌───────▼────────┐                 │
│                              │  Piper TTS     │                 │
│                              │  (multilang)   │                 │
│                              └───────┬────────┘                 │
│                                      │                          │
│                              ┌───────▼────────┐                 │
│                              │  Speaker Out   │                 │
│                              └────────────────┘                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. File & Folder Structure

```
jagruthi/
│
├── main.py                        # Entrypoint - starts all services
├── config.yaml                    # Master config (models, paths, API keys)
├── requirements.txt
├── setup.sh                       # One-shot RPi setup script
├── .env                           # GROQ_API_KEY etc.
│
├── core/
│   ├── __init__.py
│   ├── pipeline.py                # Connects STT → LLM → TTS pipeline
│   ├── session.py                 # Session state (user role, language, mood)
│   └── event_bus.py               # Async pub/sub between modules
│
├── wake/
│   ├── __init__.py
│   ├── detector.py                # openWakeWord listener
│   └── models/
│       └── hey_jagruthi.onnx      # Custom wake word model
│
├── stt/
│   ├── __init__.py
│   ├── transcriber.py             # faster-whisper wrapper
│   ├── audio_capture.py           # Mic recording (sounddevice)
│   └── language_detect.py         # Post-transcription lang detection
│
├── tts/
│   ├── __init__.py
│   ├── synthesizer.py             # Piper TTS wrapper
│   ├── player.py                  # Audio playback queue
│   └── voices/
│       ├── en_US-lessac-medium.onnx
│       ├── hi_IN-*.onnx
│       └── te_IN-*.onnx
│
├── llm/
│   ├── __init__.py
│   ├── groq_client.py             # Groq API (online)
│   ├── ollama_client.py           # Ollama fallback (offline)
│   ├── router.py                  # Picks online/offline based on connectivity
│   └── prompts/
│       ├── system_institutional.txt
│       ├── system_emotional.txt
│       ├── system_friend.txt
│       └── system_rolebase.txt    # Role-specific instructions
│
├── rag/
│   ├── __init__.py
│   ├── vectorstore.py             # ChromaDB init + CRUD
│   ├── embeddings.py              # sentence-transformers loader
│   ├── retriever.py               # Similarity search + MMR
│   ├── ingestion.py               # Ingest PDFs, DOCX, TXT, CSV
│   └── rag_chain.py               # LangChain RAG chain definition
│
├── knowledge_base/
│   ├── raw/                       # Drop source documents here
│   │   ├── timetables/
│   │   ├── faculty_directory/
│   │   ├── hostel_rules/
│   │   ├── exam_schedule/
│   │   ├── clubs_and_events/
│   │   ├── fee_structure/
│   │   ├── academic_calendar/
│   │   └── misc/
│   └── chroma_db/                 # Persisted ChromaDB files
│
├── modules/
│   ├── __init__.py
│   ├── institutional.py           # Campus info queries
│   ├── emotional_support.py       # Depression/stress detection + response
│   ├── role_manager.py            # Role detection: student/faculty/staff
│   ├── scheduler.py               # Random check-in call logic
│   ├── multilingual.py            # Language switching mid-conversation
│   └── feedback.py                # Log user ratings
│
├── hardware/
│   ├── __init__.py
│   ├── mic.py                     # Mic setup, VAD (voice activity detection)
│   ├── speaker.py                 # Speaker output control
│   ├── led.py                     # GPIO LED status indicators (optional)
│   └── display.py                 # Optional 7" screen UI
│
├── admin/
│   ├── ingest_cli.py              # CLI to add new documents
│   └── logs/
│       ├── conversations/
│       └── errors/
│
├── tests/
│   ├── test_stt.py
│   ├── test_rag.py
│   ├── test_tts.py
│   └── test_pipeline_e2e.py
│
└── scripts/
    ├── download_models.sh         # Downloads Whisper, Piper voices
    ├── install_ollama.sh
    └── warmup.py                  # Pre-loads models into RAM on boot
```

---

## 6. All Features

### 6.1 Core Features
| Feature | Description |
|---|---|
| Wake Word | "Hey Jagruthi" triggers active listening |
| Multilingual STT | English, Hindi, Telugu via Whisper |
| RAG-grounded Answers | All institutional answers cited from docs - no hallucination |
| Role-Based Responses | Student, faculty, staff get different depth/tone |
| Natural TTS | Piper voices, language-matched |
| Offline Fallback | Ollama llama3.2:3b when no internet |
| Session Memory | Remembers conversation context within session |

### 6.2 Institutional Knowledge Features
| Feature | Example Query |
|---|---|
| Timetable lookup | "What time is Dr. Rao's class tomorrow?" |
| Faculty directory | "Who is the HOD of CSE?" |
| Exam schedule | "When is my algorithms exam?" |
| Fee structure | "How much is the hostel fee?" |
| Event calendar | "What events are happening this week?" |
| Club info | "How do I join the robotics club?" |
| Academic rules | "What's the attendance policy?" |
| Hostel rules | "What's the curfew time?" |
| Grievance routing | "I want to report a problem" → routes to right person |

### 6.3 Emotional Support Features
| Feature | Description |
|---|---|
| Mood detection | Detects stress/sadness from speech + word choice |
| Empathetic persona | Switches to "friend mode" system prompt |
| Active listening | Asks open questions, does not rush to solutions |
| Coping techniques | Breathing exercises, grounding techniques via voice |
| Escalation | If severe, suggests counsellor + gives contact |
| No-judgment zone | No logs stored for emotional sessions (privacy) |

### 6.4 Companion / Social Features
| Feature | Description |
|---|---|
| Random check-ins | "Hey! How was your quiz today?" at configurable intervals |
| Name memory | Remembers user's name and preferences across sessions |
| Small talk | Can discuss cricket, movies, music naturally |
| Motivational quotes | Sends encouraging messages during exam season |
| Daily greeting | Good morning / evening based on time of day |

### 6.5 Admin Features
| Feature | Description |
|---|---|
| Document ingestion CLI | Drop PDF/DOCX/CSV → `python admin/ingest_cli.py` |
| Conversation logs | Anonymized logs for improving the system |
| Feedback collection | "Was that helpful?" → logged |
| Hot-reload knowledge | Update docs without restarting the system |

---

## 7. Model Recommendations Per Use Case

| Use Case | Model | Why |
|---|---|---|
| STT (accuracy) | `faster-whisper medium` | Best accuracy for Indian accents |
| STT (speed on RPi 4) | `faster-whisper small` | 2× faster, acceptable accuracy |
| LLM (online) | Groq `llama-3.1-70b-versatile` | Free, fast, smart |
| LLM (offline fallback) | `ollama llama3.2:3b` | Fits in 2GB RAM |
| LLM (emotional support) | Groq `llama-3.3-70b-versatile` | Better empathy |
| Embeddings | `BAAI/bge-small-en-v1.5` | Fast, accurate, multilingual |
| TTS (English) | Piper `en_US-lessac-medium` | Most natural English |
| TTS (Hindi) | Piper `hi_IN-*` | Natural Hindi prosody |
| TTS (Telugu) | Piper `te_IN-*` | Free Telugu voice |
| Wake word | `openWakeWord` | RPi-native, free |

---

## 8. RAG Pipeline Design

```
Documents (PDF/DOCX/TXT/CSV)
    │
    ▼
Text Extraction (PyMuPDF / python-docx / pandas)
    │
    ▼
Chunking (RecursiveCharacterTextSplitter, 512 tokens, 50 overlap)
    │
    ▼
Metadata tagging: {source, doc_type, role_visibility, language}
    │
    ▼
Embeddings: BAAI/bge-small-en-v1.5
    │
    ▼
ChromaDB (persistent local store)
    │
    ▼
At Query Time:
  User query → embed → MMR retrieval (k=5, diversity=0.3)
    │
    ▼
  Retrieved chunks + query → Groq LLM
    │
    ▼
  Answer with citation metadata
```

**Role-based retrieval:** Each document chunk has a `role_visibility` metadata field.
- `["student", "faculty", "staff"]` - visible to all
- `["faculty", "staff"]` - filtered from student queries
- `["staff"]` - HR/admin docs only

---

## 9. Emotional State Detection Logic

```python
# Simplified flow
sentiment = analyze_sentiment(transcribed_text)  # Using Groq

if sentiment.label in ["sad", "stressed", "anxious", "hopeless"]:
    session.mode = "emotional_support"
    system_prompt = load_prompt("system_friend.txt")
    disable_logging()  # Privacy
    if sentiment.severity == "crisis":
        tts("I'm here with you. Would you like to talk to a counsellor?")
        provide_contact()
```

Emotional triggers watched for:
- "I failed", "no one cares", "I want to give up", "I'm tired of everything"
- Voice tonality (slower speech, lower energy in audio features)
- Time context: exam week → higher sensitivity

---

## 10. Language Switching Mid-Conversation

```yaml
# config.yaml
supported_languages:
  - code: en
    name: English
    whisper_lang: en
    piper_voice: en_US-lessac-medium
  - code: hi
    name: Hindi
    whisper_lang: hi
    piper_voice: hi_IN-*
  - code: te
    name: Telugu
    whisper_lang: te
    piper_voice: te_IN-*

auto_detect: true  # Whisper detects language per utterance
```

Jagruthi mirrors the user's language automatically. If you say one sentence in Telugu and the next in Hindi, it responds in the same language.

---

## 11. Deployment on Raspberry Pi

### Boot-time systemd service:
```ini
# /etc/systemd/system/jagruthi.service
[Unit]
Description=Jagruthi Campus AI
After=network.target sound.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/jagruthi/main.py
WorkingDirectory=/home/pi/jagruthi
User=pi
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Performance tuning for RPi:
- Swap file: 4GB
- GPU memory split: 128MB (headless) or 256MB (with display)
- Use `ionice` for disk-heavy ChromaDB operations
- Pre-load Whisper + Piper into RAM at boot (`scripts/warmup.py`)
- Disable unused services (Bluetooth, Wi-Fi if wired)

---

## 12. Random Check-in System

```python
# modules/scheduler.py
import random
from apscheduler.schedulers.background import BackgroundScheduler

CHECKIN_MESSAGES = {
    "morning": ["Good morning! Ready for classes today?", "Subhodayam! Ela unnav?"],
    "exam_week": ["Hey, how's the prep going? Need help with anything?"],
    "evening": ["Long day? Want to talk?"],
    "weekend": ["No classes today - what are you up to?"]
}

def schedule_random_checkin():
    # Random interval: 2-6 hours during active hours (8am-10pm)
    delay_minutes = random.randint(120, 360)
    scheduler.add_job(trigger_checkin, 'interval', minutes=delay_minutes)
```

---

## 13. Setup Script (setup.sh)

```bash
#!/bin/bash
# Run once on fresh RPi OS

sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip portaudio19-dev ffmpeg git

pip3 install faster-whisper langchain langchain-groq chromadb \
  sentence-transformers piper-tts sounddevice apscheduler \
  openWakeWord python-dotenv PyMuPDF python-docx

# Install Ollama for offline fallback
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b

# Download Piper voices
bash scripts/download_models.sh

# Enable and start service
sudo systemctl enable jagruthi
sudo systemctl start jagruthi
```

---

## 14. Cost Breakdown

| Component | Cost |
|---|---|
| Groq API | Free (14,400 req/day) |
| Whisper (faster-whisper) | Free, local |
| ChromaDB | Free, local |
| Piper TTS | Free, local |
| openWakeWord | Free, local |
| sentence-transformers | Free, local |
| Ollama (offline) | Free, local |
| **Total running cost** | **₹0/month** |

---

## 15. Known Limitations & Mitigations

| Limitation | Mitigation |
|---|---|
| RPi 4 is slow for medium Whisper | Use `small` model; upgrade to RPi 5 if budget allows |
| Groq has rate limits | Queue + retry; offline Ollama as fallback |
| Telugu Piper voice quality varies | Mix Coqui XTTS v2 for Telugu if RPi 5 |
| No real-time internet required but preferred | Full offline mode via Ollama |
| Emotional support is not therapy | Clear escalation to real counsellor |
| Multiple users at kiosk | Session reset on silence timeout (30s) |

---

## 16. Roadmap (Phases)

### Phase 1 - Core (Week 1-2)
- [ ] RPi OS setup, mic/speaker test
- [ ] Whisper STT working
- [ ] Piper TTS working (English)
- [ ] Basic LangChain RAG with ChromaDB
- [ ] Groq LLM integration

### Phase 2 - Intelligence (Week 3-4)
- [ ] Document ingestion pipeline
- [ ] Role-based filtering
- [ ] Wake word detection
- [ ] Hindi + Telugu TTS voices
- [ ] Offline Ollama fallback

### Phase 3 - Personality (Week 5-6)
- [ ] Emotional support chain
- [ ] Session memory
- [ ] Random check-in scheduler
- [ ] Language auto-detection

### Phase 4 - Deployment (Week 7-8)
- [ ] Systemd service
- [ ] Admin CLI for document updates
- [ ] 3D printed kiosk enclosure
- [ ] Campus pilot with 20 users
- [ ] Feedback collection + iteration

---

*Jagruthi - "Awakening" in Telugu. The name says it all.*