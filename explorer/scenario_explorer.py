from __future__ import annotations

from pathlib import Path
from time import sleep
from typing import TypedDict, cast

import uiautomator2
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.constants import START
from langgraph.graph import StateGraph
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
from explorer.utils import get_file_content

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

    user_request: str
    user_scenario: Scenario
    trace: list[ActionFrame]


class ScenarioExplorer:
    """High level scenario execution engine."""

    def __init__(self, model: BaseChatModel) -> None:
        graph_builder = StateGraph(ExplorerState)
        graph_builder.add_node("extract_scenario", self._extract_scenario)
        graph_builder.add_node("explore", self._explore)

        graph_builder.add_edge(START, "extract_scenario")
        graph_builder.add_edge("extract_scenario", "explore")

        self._graph = graph_builder.compile()
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

    def _extract_scenario(self, state: ExplorerState) -> ExplorerState:
        parser = PydanticOutputParser(pydantic_object=Scenario)
        prompt_path = (
            Path(__file__).parent / "prompts" / "extract_step_by_step_scenario.md"
        )
        template_str = get_file_content(str(prompt_path))
        request = PromptTemplate.from_template(template_str).invoke(
            {
                "scenario": state["user_request"],
                "format_instructions": parser.get_format_instructions(),
            }
        )
        response = self._model.invoke(request)
        state["user_scenario"] = parser.parse(response.text())
        return state

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

    def explore(self, request: str) -> list[ActionFrame]:
        result = self._graph.invoke({"user_request": request})
        return result["trace"]

    def run_trace(self, trace: list[ActionFrame]) -> list[ActionFrame]:
        """Replay a saved trace without using the language model."""

        state = cast(ExplorerState, {"trace": trace})
        result = self._explore(state)
        return result["trace"]
