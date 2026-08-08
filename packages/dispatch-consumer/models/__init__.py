from dataclasses import dataclass, field
from datetime import datetime

from db.models import STATUS_ORDER, ActiveCall  # pyright: ignore[reportUnusedImport]

@dataclass
class GroupedResponder:
    unit: str
    agency: str
    dispatch_area: str
    statuses: list[str] = field(default_factory=list)

@dataclass
class GroupedEvent:
    external_id: str
    time_received: str
    parsed_time: datetime
    call_type: str
    location: str
    responders: list[GroupedResponder] = field(default_factory=list)