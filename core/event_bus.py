import asyncio
import logging
from collections import defaultdict
from typing import Callable, Any
 
log = logging.getLogger(__name__)
 
 
class EventBus:
    """Simple async pub/sub event bus."""
 
    def __init__(self):
        self._listeners: dict[str, list[Callable]] = defaultdict(list)
 
    def subscribe(self, event: str, handler: Callable):
        self._listeners[event].append(handler)
        log.debug("Subscribed %s to event '%s'", handler.__name__, event)
 
    def unsubscribe(self, event: str, handler: Callable):
        self._listeners[event] = [h for h in self._listeners[event] if h != handler]
 
    async def publish(self, event: str, data: Any = None):
        for handler in self._listeners.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                log.error("Error in handler %s for event %s: %s", handler.__name__, event, e)
 
 
# Global singleton
bus = EventBus()