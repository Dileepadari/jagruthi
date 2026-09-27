import asyncio
import logging
import random
from datetime import datetime
 
from apscheduler.schedulers.background import BackgroundScheduler
 
log = logging.getLogger(__name__)
 
CHECKIN_MESSAGES = {
    "morning": [
        "Good morning! Hope you're ready for the day ahead. Can I help with anything?",
        "Subhodayam! Need any information before classes start?",
    ],
    "afternoon": [
        "Hey! How's the day going? Need help with anything?",
        "Just checking in - any questions about campus today?",
    ],
    "exam": [
        "Hey, exam season can be tough. How are you holding up?",
        "Just wanted to check in. How is your exam preparation going?",
    ],
    "evening": [
        "Long day? I'm here if you need anything.",
        "Good evening! Anything I can help you with before the day ends?",
    ],
    "weekend": [
        "Happy weekend! Any campus information you need?",
        "Hey! Hope you're getting some rest. I'm here if you need anything.",
    ],
}
 
 
def _pick_message() -> str:
    now  = datetime.now()
    hour = now.hour
    day  = now.weekday()
 
    if day >= 5:
        bucket = "weekend"
    elif 8 <= hour < 12:
        bucket = "morning"
    elif 12 <= hour < 17:
        bucket = "afternoon"
    else:
        bucket = "evening"
 
    return random.choice(CHECKIN_MESSAGES[bucket])
 
 
class CheckInScheduler:
    def __init__(self, config: dict, pipeline):
        self.config   = config["scheduler"]
        self.pipeline = pipeline
        self._sched   = BackgroundScheduler()
        self._loop    = asyncio.get_event_loop()
 
    def start(self):
        if not self.config.get("enabled", True):
            return
        self._schedule_next()
        self._sched.start()
        log.info("Check-in scheduler started.")
 
    def stop(self):
        if self._sched.running:
            self._sched.shutdown(wait=False)
 
    def _schedule_next(self):
        mn = self.config["min_interval_hours"] * 3600
        mx = self.config["max_interval_hours"] * 3600
        delay_s = random.randint(int(mn), int(mx))
        log.debug("Next check-in in %.0f minutes", delay_s / 60)
        self._sched.add_job(
            self._fire,
            trigger="interval",
            seconds=delay_s,
            id="checkin",
            replace_existing=True,
            max_instances=1,
        )
 
    def _fire(self):
        now  = datetime.now().hour
        start = self.config["active_hours_start"]
        end   = self.config["active_hours_end"]
        if not (start <= now < end):
            log.debug("Check-in suppressed (outside active hours)")
            self._schedule_next()
            return
 
        message = _pick_message()
        log.info("Check-in: %s", message)
        asyncio.run_coroutine_threadsafe(
            self.pipeline.speak_checkin(message), self._loop
        )
        self._schedule_next()