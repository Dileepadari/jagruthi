<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./docs/assets/adk_dev_logo_light.png">
  <img src="./docs/assets/adk_dev_logo_dark.png" width="150" alt="ADK DEV" loading="lazy">
</picture>
<br>
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./docs/assets/jagruthi-logo-dark.png">
  <img src="./docs/assets/jagruthi-logo-light.png" width="720" alt="Jagruthi, a voice kiosk for the campus" loading="lazy">
</picture>
<br>
<img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" loading="lazy">
<img alt="Raspberry Pi" src="https://img.shields.io/badge/Raspberry_Pi-A22846?style=for-the-badge&logo=raspberrypi&logoColor=white" loading="lazy">
<img alt="Whisper" src="https://img.shields.io/badge/faster--whisper-000000?style=for-the-badge&logo=openai&logoColor=white" loading="lazy">
<br>
<img alt="ChromaDB" src="https://img.shields.io/badge/ChromaDB-FFB000?style=for-the-badge" loading="lazy">
<img alt="Ollama" src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" loading="lazy">
<img alt="MIT License" src="https://img.shields.io/badge/License-MIT-3DA639?style=for-the-badge" loading="lazy">

<br><br>

**[Developer documentation](./DEVDOC.md)** &middot; [How a turn works](#how-a-turn-works) &middot; [The crisis path](#the-crisis-path) &middot; [Quick start](#quick-start)

</div>

---

# Jagruthi - Campus Conversational AI Kiosk

A voice kiosk for a college campus. Say the wake word, ask a question out loud, get an answer out loud. It answers institutional questions from documents you feed it (timetables, hostel rules, department directories) and it will also just talk to a student who is having a bad day.

Runs on a Raspberry Pi, and offline when it has to be: wake word and speech recognition are local, and if the internet is down it falls back from Groq to a local Ollama model.

> [!IMPORTANT]
> **Set `emotional.counsellor_contact` in `config.yaml` before deploying this.** It ships as the placeholder `+91-XXXXXXXXXX`. The kiosk detects a placeholder and will name the counsellor and room rather than read out a fake number, but a student in distress should be given a real one. See [The crisis path](#the-crisis-path).

## How a turn works

```
wake word  ->  record  ->  transcribe  ->  is this person alright?
                                                |
                                     no --------+-------- yes
                                     |                      |
                            emotional support        campus question?
                            (+ counsellor                   |
                             details if a           yes ----+---- no
                             crisis)                 |            |
                                                    RAG      friendly chat
                                                     |            |
                                                     +-----+------+
                                                           |
                                                     speak the answer
```

| Stage | What does it |
|---|---|
| Wake word | openWakeWord, local, 80ms frames |
| Speech to text | faster-whisper, local, auto language detect |
| Languages | English, Hindi, Telugu |
| Answering | Groq (Llama 3.3 70B) when online, Ollama (Llama 3.2 3B) when not |
| Documents | ChromaDB with BAAI/bge-small-en-v1.5 embeddings |
| Text to speech | Piper, per-language voices |

## Quick start

```bash
# 1. Add your Groq API key (free at console.groq.com)
echo "GROQ_API_KEY=your_key_here" > .env

# 2. Run full setup
bash setup.sh

# 3. Drop campus documents into knowledge_base/raw/
#    (PDFs, DOCX, TXT, CSV - any folder under raw/)

# 4. Ingest documents
source venv/bin/activate
bash scripts/download_models.sh
python3 admin/ingest_cli.py

# 5. Set the counsellor contact
$EDITOR config.yaml        # emotional.counsellor_contact

# 6. Run Jagruthi
python3 main.py
```

## Voice commands

- Say **"Hey Jagruthi"** (default wake word) to activate
- Ask anything: "When is the exam?", "Who is the HOD of CSE?", "What are hostel rules?"

## Add documents

```bash
cp my_timetable.pdf knowledge_base/raw/timetables/
python3 admin/ingest_cli.py
```

## Check DB status

```bash
python3 admin/ingest_cli.py --status
```

## The crisis path

This is the part of the code that matters most, so it is worth saying plainly what it does.

Every utterance is checked against a keyword list before anything else. A crisis phrase short-circuits straight to `crisis` and is never sent to the model for a second opinion, so a model answering "neutral" cannot disarm it. Softer signals ("overwhelmed", "can't sleep") go to the LLM for triage, and if the LLM cannot be reached they are treated as real rather than dismissed.

The phrases cover English, Hindi and Telugu, in script and in the romanised spelling Whisper tends to produce. That matters: the kiosk advertises three languages, and a crisis said in the other two used to score `neutral`.

When the mood is `crisis`, the counsellor's details are built **without the model** and appended no matter what. If the LLM times out, if the network is down, if the prompt file is missing, the student still hears who to talk to. A turn that fails is caught and logged and the kiosk carries on listening, rather than dying and spending a minute reloading Whisper before it can hear anyone again.

Emotional sessions are never written to `admin/logs/interactions.csv`.

None of this makes it a mental health service. It is a kiosk that knows when to hand over to a person.

## Running the checks

```bash
pip install pytest pyyaml
pytest tests/ -v            # 73 tests, no models or network needed
python3 ops/check_config.py
ops/hygiene.sh
```

CI runs all of it on push and pull request, on Python 3.11 and 3.12.

The tests deliberately do not install `requirements.txt`: faster-whisper, chromadb and sentence-transformers are hundreds of megabytes, and RPi.GPIO will not install off a Pi. Everything under test is pure logic that imports none of them. What that leaves untested is listed in [not_for_you.md](not_for_you.md).

## Layout

| Path | What is in it |
|---|---|
| `main.py` | Entry point |
| `core/` | Pipeline, session state, event bus |
| `wake/`, `stt/`, `tts/` | Wake word, speech to text, speech synthesis |
| `llm/` | Groq and Ollama clients, the router between them, prompts |
| `rag/` | Ingestion, embeddings, vector store, retrieval chain |
| `modules/` | Emotional support, role detection, language, scheduler, logging |
| `hardware/` | LED, mic, speaker and display on the Pi |
| `admin/` | Document ingestion CLI |
| `ops/` | Config check and hygiene tripwires |
| `tests/` | Pure-logic tests |

[DEVDOC.md](DEVDOC.md) has the rest: the trust boundaries, and the things that will surprise you.

## License

MIT. See [LICENSE](LICENSE).

---

*Jagruthi - "Awakening" in Telugu.*
