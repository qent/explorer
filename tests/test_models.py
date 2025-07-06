import json
from typing import cast

from explorer.models import (
    ActionFrame,
    ActionInfo,
    ActionType,
    ElementInfo,
    Error,
    ScreenInfo,
)

# mypy: ignore-errors


def test_action_frame_to_dict() -> None:
    frame = ActionFrame(
        screen=ScreenInfo(name="main", description="", hierarchy="<hierarchy/>"),
        action=ActionInfo(
            element=ElementInfo(description="btn"), type=ActionType.CLICK
        ),
        error=Error(type="SomeError", message="oops"),
    )
    data = frame.to_dict()
    screen = cast(dict[str, str], data["screen"])
    action = cast(dict[str, str], data["action"])
    error = cast(dict[str, str], data["error"])
    assert screen["name"] == "main"
    assert action["type"] == ActionType.CLICK
    assert error["type"] == "SomeError"
    json.dumps(data)  # Ensure serializable
