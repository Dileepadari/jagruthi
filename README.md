# Jagruthi — Campus Conversational AI Kiosk
 
## Quick Start
 
```bash
# 1. Add your Groq API key (free at console.groq.com)
echo "GROQ_API_KEY=your_key_here" > .env
 
# 2. Run full setup
bash setup.sh
 
# 3. Drop campus documents into knowledge_base/raw/
#    (PDFs, DOCX, TXT, CSV — any folder under raw/)
 
# 4. Ingest documents
source venv/bin/activate
bash scripts/download_models.sh
python3 admin/ingest_cli.py
 
# 5. Run Jagruthi
python3 main.py
```
 
## Voice Commands
- Say **"Hey Jagruthi"** (default wake word) to activate
- Ask anything: "When is the exam?", "Who is the HOD of CSE?", "What are hostel rules?"
 
## Add Documents
```bash
cp my_timetable.pdf knowledge_base/raw/timetables/
python3 admin/ingest_cli.py
```
 
## Check DB Status
```bash
python3 admin/ingest_cli.py --status
```