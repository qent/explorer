from typing import Any, Dict, Optional, TypedDict


class ActionFrame(TypedDict):
    """Description of a single action performed during scenario exploration."""

    element: Dict[str, Any]
    type: str
    data: Optional[str]
