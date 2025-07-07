from __future__ import annotations

from time import sleep
from typing import TypedDict, cast

import uiautomator2
from langchain_core.language_models import BaseChatModel
from uiautomator2 import XPathElementNotFoundError

from explorer.element_navigator import ElementNavigator
from explorer.models import (
    ActionFrame,
    ActionInfo,
    ActionType,
    Error,
    ExecutionStatus,
    Scenario,
    ScreenInfo,
)

# mypy: ignore-errors


VALID_KEYS: set[str] = {
    "home",
    "back",
    "left",
    "right",
    "up",
    "down",
    "center",
    "menu",
    "search",
    "enter",
    "delete",
    "recent",
    "volume_up",
    "volume_down",
    "volume_mute",
    "camera",
    "power",
}


class ExplorerState(TypedDict, total=False):
    """State shared across scenario execution steps."""

    user_scenario: Scenario
    trace: list[ActionFrame]


class ScenarioExplorer:
    """High level scenario execution engine."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    @staticmethod
    def _perform_action(device: uiautomator2.Device, action: ActionInfo) -> None:
        """Execute ``action`` on ``device`` without using the language model."""

        if action.type is ActionType.PRESS_KEY:
            key = cast(str, action.data)
            device.press(key)
            action.status = ExecutionStatus.EXECUTED
            return

        if action.type is ActionType.SWIPE_SCREEN:
            width, height = device.window_size()
            direction = cast(str, action.data)
            margin = 100
            if direction == "up":
                fx, fy, tx, ty = width // 2, height - margin, width // 2, margin
            elif direction == "down":
                fx, fy, tx, ty = width // 2, margin, width // 2, height - margin
            elif direction == "left":
                fx, fy, tx, ty = width - margin, height // 2, margin, height // 2
            else:  # right
                fx, fy, tx, ty = margin, height // 2, width - margin, height // 2
            device.swipe(fx, fy, tx, ty)
            action.status = ExecutionStatus.EXECUTED
            return

        assert action.element is not None
        selector = device.xpath(cast(str, action.element.xpath))

        if action.type is ActionType.SWIPE_ELEMENT:
            selector.swipe(cast(str, action.data))
            action.status = ExecutionStatus.EXECUTED
            return

        if action.type is ActionType.TEXT_INPUT:
            selector.click()
            sleep(3)
            if action.data:
                device.send_keys(action.data)
        else:
            selector.click()
        action.status = ExecutionStatus.EXECUTED

    def _explore(self, state: ExplorerState) -> ExplorerState:
        device = uiautomator2.connect()
        element_navigator = ElementNavigator(self._model, device)

        if not state.get("trace"):
            state["trace"] = [
                ActionFrame(screen=None, action=action, error=None)
                for action in cast(Scenario, state["user_scenario"]).actions
            ]

        for frame in state["trace"]:
            action = frame.action

            if action.status is ExecutionStatus.EXECUTED:
                try:
                    self._perform_action(device, action)
                except XPathElementNotFoundError:
                    frame.error = Error(type="XPathElementNotFoundError", message=None)
                    frame.screen = ScreenInfo(
                        name="",
                        description="",
                        hierarchy=element_navigator.full_hierarchy,
                    )
                    action.status = ExecutionStatus.BROKEN
                    break
                continue

            if action.type is ActionType.PRESS_KEY:
                key = cast(str, action.data)
                if key not in VALID_KEYS:
                    frame.error = Error(type="InvalidKeyError", message=None)
                    frame.screen = ScreenInfo(
                        name="",
                        description="",
                        hierarchy=element_navigator.full_hierarchy,
                    )
                    action.status = ExecutionStatus.BROKEN
                    break
                frame.screen = ScreenInfo(
                    name="",
                    description="",
                    hierarchy=element_navigator.full_hierarchy,
                )
                self._perform_action(device, action)
                continue

            if action.type is ActionType.SWIPE_SCREEN:
                frame.screen = ScreenInfo(
                    name="",
                    description="",
                    hierarchy=element_navigator.full_hierarchy,
                )
                self._perform_action(device, action)
                continue

            try:
                assert action.element is not None
                info = cast(
                    dict[str, object],
                    element_navigator.find_element_info(action.element.description),
                )
                element_dict = cast(dict[str, object], info.get("element", {}))
                screen = ScreenInfo(
                    name=cast(str, element_dict.get("screen", "")),
                    description=cast(str, element_dict.get("screen_description", "")),
                    hierarchy=element_navigator.full_hierarchy,
                )
                frame.screen = screen
                action.element.name = cast(str | None, element_dict.get("name"))
                action.element.xpath = cast(str | None, element_dict.get("xpath"))
                try:
                    self._perform_action(device, action)
                except XPathElementNotFoundError:
                    frame.error = Error(type="XPathElementNotFoundError", message=None)
                    frame.screen = ScreenInfo(
                        name="",
                        description="",
                        hierarchy=element_navigator.full_hierarchy,
                    )
                    action.status = ExecutionStatus.BROKEN
                    break
            except LookupError:
                frame.error = Error(type="ElementNotFoundError", message=None)
                frame.screen = ScreenInfo(
                    name="",
                    description="",
                    hierarchy=element_navigator.full_hierarchy,
                )
                action.status = ExecutionStatus.BROKEN
                break

        device.stop_uiautomator()
        return state

    def explore(self, scenario: list[ActionInfo]) -> list[ActionFrame]:
        """Execute a prepared scenario."""

        state = cast(ExplorerState, {"user_scenario": Scenario(actions=scenario)})
        result = self._explore(state)
        return result["trace"]

    def run_trace(self, trace: list[ActionFrame]) -> list[ActionFrame]:
        """Replay a saved trace without using the language model."""

        state = cast(ExplorerState, {"trace": trace})
        result = self._explore(state)
        return result["trace"]
