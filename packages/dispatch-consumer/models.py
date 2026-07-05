from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActiveCall:
    time_received: str
    agency: str
    dispatch_area: str
    unit: str
    call_type: str
    location: str
    status: str

    @property
    def call_id(self) -> str:
        key = "|".join(
            (
                self.agency,
                self.unit,
                self.call_type,
                self.location,
            )
        )
        return hashlib.sha256(key.encode()).hexdigest()
