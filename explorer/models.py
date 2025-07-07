from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

# mypy: ignore-errors


class ActionType(str, Enum):
    CLICK = "click"
    TEXT_INPUT = "text_input"
    PRESS_KEY = "press_key"
    SWIPE_ELEMENT = "swipe_element"
    SWIPE_SCREEN = "swipe_screen"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    BROKEN = "broken"


class ElementInfo(BaseModel):
    """Information about an element on the device screen."""

    name: Optional[str] = Field(None, description="Device element name")
    description: str = Field(description="Short description of element")
    xpath: Optional[str] = Field(None, description="Element xpath")


class ActionInfo(BaseModel):
    """Description of a single action to perform on the device."""

    element: Optional[ElementInfo] = Field(
        None,
        description=(
            "Element to interact with. ``None`` for actions without a UI element"
        ),
    )
    data: Optional[str] = Field(
        None,
        description=(
            "Additional data required for the action. This is used for text input, "
            "swipe direction or key name."
        ),
    )
    type: ActionType = Field(
        ActionType.CLICK,
        description="Action type ('click', 'text_input', 'press_key', etc)",
    )
    status: ExecutionStatus = Field(
        ExecutionStatus.PENDING,
        description="Action executions status ('pending', 'executed', 'broken', etc)",
    )


class Scenario(BaseModel):
    """Model of the interaction scenario with the application"""

    actions: List[ActionInfo] = Field(
        description="An ordered list of step-by-step actions on application"
    )


@dataclass
class ScreenInfo:
    """Description of the current screen."""

    name: str
    description: str
    hierarchy: str
    image: Optional[str] = None


@dataclass
class Error:
    """Error occurred during action execution."""

    type: str
    message: Optional[str]


@dataclass
class ActionFrame:
    """State of a single action during scenario execution."""

    screen: Optional[ScreenInfo]
    action: ActionInfo
    error: Optional[Error]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON serialisable representation of the frame."""

        return {
            "screen": asdict(self.screen) if self.screen else None,
            "action": self.action.model_dump(),
            "error": asdict(self.error) if self.error else None,
        }
