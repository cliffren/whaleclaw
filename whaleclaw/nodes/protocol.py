"""Node capability definitions."""

from __future__ import annotations

from enum import StrEnum


class NodeCapability(StrEnum):
    """Device node capability identifiers."""

    CAMERA_SNAP = "camera.snap"
    CAMERA_CLIP = "camera.clip"
    SCREEN_RECORD = "screen.record"
    LOCATION_GET = "location.get"
    NOTIFICATION = "notification"
    SYSTEM_RUN = "system.run"
