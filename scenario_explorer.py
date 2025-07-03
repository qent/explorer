from __future__ import annotations

from enum import Enum
from time import sleep
from typing import List, Optional, TypedDict, cast

import uiautomator2
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.constants import START
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field
from uiautomator2 import XPathElementNotFoundError

from explorer.action_frame import ActionFrame
from explorer.element_navigator import ElementNavigator
from explorer.utils import get_file_content

# mypy: ignore-errors


class ActionType(str, Enum):
    CLICK = "click"
    TEXT_INPUT = "text_input"


class Step(BaseModel):
    """Model of action with interface element"""

    element: str = Field(description="Short description of element for action")
    data: Optional[str] = Field(
        None, description="Data required for an action, such as text for a text input"
    )
    action: ActionType = Field(
        ActionType.CLICK, description="Action type ('click', 'text_input', etc)"
    )


class Scenario(BaseModel):
    """Model of the interaction scenario with the application interface"""

    steps: List[Step] = Field(
        description="An ordered list of step-by-step actions on interface elements"
    )


class ExplorerState(TypedDict):
    user_request: str
    user_scenario: Scenario
    actual_scenario: Scenario
    trace: list[ActionFrame]


class ScenarioExplorer:
    def __init__(self, model: BaseChatModel):
        graph_builder = StateGraph(ExplorerState)
        graph_builder.add_node("extract_scenario", self._extract_scenario)
        graph_builder.add_node("explore", self._explore)

        graph_builder.add_edge(START, "extract_scenario")
        graph_builder.add_edge("extract_scenario", "explore")

        self._graph = graph_builder.compile()
        self._model = model

    def _extract_scenario(self, state: ExplorerState) -> ExplorerState:
        parser = PydanticOutputParser(pydantic_object=Scenario)
        request = PromptTemplate.from_template(
            get_file_content("./explorer/prompts/extract_step_by_step_scenario.md")
        ).invoke(
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
        state["trace"] = []

        for step in state["user_scenario"].steps:
            try:
                element_info = cast(
                    dict[str, object], element_navigator.find_element_info(step.element)
                )
                try:
                    selector = device.xpath(element_info["element"]["xpath"])

                    if step.action is ActionType.TEXT_INPUT:
                        selector.click()
                        sleep(3)
                        device.send_keys(step.data)
                        action = ActionFrame(
                            element=element_info, type=step.action, data=step.data
                        )
                    else:
                        selector.click()
                        action = ActionFrame(
                            element=element_info, type=step.action, data=None
                        )

                    state["trace"].append(action)
                except XPathElementNotFoundError:
                    interruption = ActionFrame(
                        element=element_info,
                        type="INTERRUPTION",
                        data="XPathElementNotFoundError",
                    )
                    state["trace"].append(interruption)
                    break
            except LookupError:
                element_info = {
                    "hierarchy": element_navigator.full_hierarchy,
                    "element_request": step.element,
                }
                interruption = ActionFrame(
                    element=element_info,
                    type="INTERRUPTION",
                    data="ElementNotFoundError",
                )
                state["trace"].append(interruption)

        device.stop_uiautomator()
        return state

    def explore(self, request: str) -> list[ActionFrame]:
        result = self._graph.invoke({"user_request": request})
        return result["trace"]
