# Not for you

An honest list of reasons to close this tab.

**You want a mental health service.** This is a kiosk with a keyword list and a language model. It has no clinician, no escalation to anyone who is on call, no follow-up, and no record that a conversation happened (emotional sessions are deliberately not logged). What it does is notice alarming words and tell a student who to go and see. If you need something that carries actual duty of care, this is not it, and pointing students at it as though it were would be worse than having nothing.

**You want the crisis detection to be reliable.** It is a substring match against a list of phrases in three languages, backed by a model asked to reply with one word. It will miss sarcasm, indirection, anything phrased unusually, any language other than English, Hindi and Telugu, and anything Whisper mishears. It errs towards escalating, which means it will also sometimes offer a counsellor to someone who just failed a quiz.

**You want it to run anywhere.** It is written for a Raspberry Pi with a microphone and a speaker. `requirements.txt` pins `RPi.GPIO`, which does not install elsewhere; the systemd unit hardcodes `/home/pi/Desktop/Jagruthi`; the LED module is a no-op without GPIO. It will run on a laptop for development, but that is not what it is.

**You want a tested speech pipeline.** The tests cover the pure logic: triage, role detection, language codes, session state, LLM routing. They cover none of Whisper, Piper, ChromaDB, openWakeWord or the audio capture, because each of those needs hundreds of megabytes of models or the hardware itself. That is most of the interesting failure surface, and it is verified by running the thing on a Pi and listening to it.

**You want document answers you can trust.** RAG is routed by a keyword list: if your question does not contain one of about forty campus words, it never touches the vector store and the model answers from its own weights instead. "Who is the HOD?" hits RAG. "Who should I talk to about my project?" does not.

**You want an admin dashboard.** `Plan.md` mentions an optional Flask dashboard. It was never written; the empty file that stood in for it has been removed. Document ingestion is a CLI.

**You want multi-user, accounts or privacy controls.** There is one kiosk, one session at a time, no identity, and a CSV of every non-emotional interaction on the Pi's SD card. Anyone who can reach the device can read it.

**You want it to keep working when Groq changes its models.** The router disables Groq for the rest of the run when it sees a `model_decommissioned` error and falls back to Ollama, which is a much smaller model. Answers get noticeably worse rather than stopping. The model names are in `config.yaml` and will need updating.

**You want the starter configuration to be safe to deploy.** It is not. `emotional.counsellor_contact` is `+91-XXXXXXXXXX` and `campus.name` is somebody else's campus. The code refuses to read out the placeholder number, but the point stands: read `config.yaml` before this talks to anyone.
