import asyncio
import logging
import signal
import sys
from pathlib import Path
 
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
 
load_dotenv()
console = Console()
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("admin/logs/jagruthi.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
log = logging.getLogger("jagruthi.main")
 
 
def load_config() -> dict:
    with open("config.yaml") as f:
        return yaml.safe_load(f)
 
 
async def main():
    config = load_config()
 
    console.print(
        Panel(
            f"[bold blue]Jagruthi v{config['app']['version']}[/bold blue]\\n"
            f"Campus Conversational AI · {config['campus']['name']}",
            expand=False,
        )
    )
 
    # Import here so errors surface cleanly after config load
    from core.pipeline import Pipeline
    from modules.scheduler import CheckInScheduler
    from hardware.led import LED
    from scripts.warmup import warmup
 
    led = LED()
    led.booting()
 
    log.info("Warming up models...")
    console.print("[yellow]Loading models into RAM...[/yellow]")
    await asyncio.get_event_loop().run_in_executor(None, warmup, config)
 
    pipeline = Pipeline(config)
    await pipeline.initialize()
 
    scheduler = CheckInScheduler(config, pipeline)
    scheduler.start()
 
    led.ready()
    console.print(
        f"[green]Ready.[/green] Say '[bold]{config['app']['wake_word'].replace('_', ' ')}[/bold]' to begin."
    )
 
    loop = asyncio.get_running_loop()
 
    def _shutdown(sig, frame):
        log.info("Shutdown signal received")
        scheduler.stop()
        led.off()
        loop.stop()
 
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
 
    try:
        await pipeline.run_forever()
    except asyncio.CancelledError:
        pass
    finally:
        log.info("Jagruthi stopped.")
 
 
if __name__ == "__main__":
    asyncio.run(main())