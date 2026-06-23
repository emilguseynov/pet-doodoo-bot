from __future__ import annotations

from src.bot import texts
from src.db.models import DefecationLocation, DefecationType


def event_title_from_values(*, event_type: str, location: str) -> str:
    if event_type == DefecationType.TOILET:
        return texts.EVENT_TITLE_TOILET
    try:
        loc = DefecationLocation(location)
    except ValueError:
        return f"{texts.ACCIDENT_TITLE_PREFIX}{location}"
    label = texts.LOCATION_LABELS.get(loc, location)
    return f"{texts.ACCIDENT_TITLE_PREFIX}{label}"
