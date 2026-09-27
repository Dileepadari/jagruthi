import logging
 
log = logging.getLogger(__name__)
 
# GPIO pin assignments (BCM numbering)
PIN_READY    = 17   # Green LED
PIN_THINKING = 27   # Yellow LED
PIN_SPEAKING = 22   # Blue LED
 
_gpio_available = False
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for p in (PIN_READY, PIN_THINKING, PIN_SPEAKING):
        GPIO.setup(p, GPIO.OUT, initial=GPIO.LOW)
    _gpio_available = True
except Exception:
    log.debug("RPi.GPIO not available - LED control disabled")
 
 
class LED:
    def _set(self, ready=0, think=0, speak=0):
        if not _gpio_available:
            return
        import RPi.GPIO as GPIO
        GPIO.output(PIN_READY,    GPIO.HIGH if ready else GPIO.LOW)
        GPIO.output(PIN_THINKING, GPIO.HIGH if think else GPIO.LOW)
        GPIO.output(PIN_SPEAKING, GPIO.HIGH if speak else GPIO.LOW)
 
    def booting(self):   self._set(1, 1, 1)
    def ready(self):     self._set(ready=1)
    def listening(self): self._set(ready=1, think=1)
    def thinking(self):  self._set(think=1)
    def speaking(self):  self._set(speak=1)
    def off(self):       self._set()
    # backwards-compat alias used in older setup.sh
    def set_status(self, s: str):
        {"booting": self.booting, "ready": self.ready, "off": self.off}.get(s, self.ready)()