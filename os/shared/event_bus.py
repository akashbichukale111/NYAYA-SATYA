"""Cross-Project Event Bus and Audit Trail for NYAYA-SATYA OS.
Allows loosely coupled engines to broadcast events and log tamper-evident actions.
"""

from typing import List, Callable, Dict
from datetime import datetime
from contracts.models import CrossProjectEvent, CrossProjectEventType


class EventBus:
    def __init__(self):
        self._history: List[CrossProjectEvent] = []
        self._subscribers: Dict[CrossProjectEventType, List[Callable[[CrossProjectEvent], None]]] = {}

    def subscribe(self, event_type: CrossProjectEventType, handler: Callable[[CrossProjectEvent], None]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(self, event: CrossProjectEvent):
        self._history.append(event)
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"[EventBus] Error in handler for {event.event_type}: {e}")

    def get_history(self, case_id: str = None) -> List[CrossProjectEvent]:
        if case_id:
            return [e for e in self._history if e.case_id == case_id]
        return list(self._history)


event_bus = EventBus()
