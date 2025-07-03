from typing import Optional, TypedDict


class ActionFrame(TypedDict):
    element: dict
    type: str
    data: Optional[str]
