from __future__ import annotations

import logging
from typing import Annotated, TypedDict

from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage
from langchain_core.prompts import PromptTemplate
from langgraph.constants import END, START
from langgraph.graph import StateGraph, add_messages
from langgraph.types import RetryPolicy
from uiautomator2 import Device
from uiautomator2.xpath import XPathError

from explorer.viewnode import ViewNode, parse_xml_to_tree, without_fields

# mypy: ignore-errors


logging.basicConfig(level=logging.INFO)


class AgentState(TypedDict):
    hierarchy: list[ViewNode]
    element_request: str
    element: dict[str, object]
    messages: Annotated[list[AnyMessage], add_messages]


class ElementNotFoundException(LookupError):
    hierarchy: str


class ElementNavigator:
    screen_name_schema = ResponseSchema(
        name="screen",
        description="Come up with a concise screen name for the class name in autotests "
        "that describes this hierarchy of elements",
    )

    screen_description_schema = ResponseSchema(
        name="screen_description",
        description="Come up with a short description of the application screen, "
        "it is necessary to list all the main interface elements with which the user can interact",
    )

    element_name_schema = ResponseSchema(
        name="name",
        description="Come up with a concise target element name for the screen object field name in autotests",
    )

    xpath_schema = ResponseSchema(
        name="xpath",
        description="Extract the short XPath for the target element from the hierarchy. "
        "First of all try to search by id or description!!! "
        "Find deepest view in hierarchy!!! "
        "The XPath should be abstract and universal, and **should not depend on the specific data** "
        "being displayed (names, dates, exchange rates, prices, specific weather, etc.)!!!",
    )

    logger = logging.getLogger(__name__)

    def __init__(self, model: BaseChatModel, device: Device):
        self._device = device
        self._model = model

        self.full_hierarchy = ""

        tasks = "1. " + self.screen_name_schema.description
        tasks += "\n2. " + self.screen_description_schema.description
        tasks += "\n3. " + self.element_name_schema.description
        tasks += "\n4. " + self.xpath_schema.description

        response_schemas = [
            self.screen_name_schema,
            self.screen_description_schema,
            self.element_name_schema,
            self.xpath_schema,
        ]
        self._output_parser = StructuredOutputParser.from_response_schemas(
            response_schemas
        )

        self._return_element_info_prompt_template = PromptTemplate.from_template(
            """
Here is the hierarchy of UI-elements of the android application screen. 
Analyze this hierarchy and complete the following tasks with target element = "{screen_element}":
"""
            + tasks
            + """

Elements hierarchy:
{hierarchy}

{format_instructions}
"""
        )

        self._find_view_prompt_template = PromptTemplate.from_template(
            """
Here is the hierarchy of elements of the android application screen, answer with one word YES or NO. 
There is something similar or related to "{screen_element}" on the screen?

Elements hierarchy:
{hierarchy}"""
        )

        graph_builder = StateGraph(AgentState)

        graph_builder.add_node(
            "find_element",
            self._find_element,
            retry=RetryPolicy(max_attempts=3, retry_on=(LookupError,)),
        )
        graph_builder.add_node("get_element_info", self._get_element_info)
        graph_builder.add_node("find_another_xpath", self._find_another_xpath)

        graph_builder.add_edge(START, "find_element")
        graph_builder.add_edge("find_element", "get_element_info")
        graph_builder.add_conditional_edges(
            "get_element_info", self._only_one_element_with_this_xpath
        )
        graph_builder.add_conditional_edges(
            "find_another_xpath", self._only_one_element_with_this_xpath
        )

        self._graph = graph_builder.compile()

    def _find_element(self, state: AgentState) -> AgentState:
        self.full_hierarchy = self._device.dump_hierarchy(max_depth=100)
        state["hierarchy"] = parse_xml_to_tree(self.full_hierarchy)

        request = self._find_view_prompt_template.invoke(
            {
                "screen_element": state["element_request"],
                "hierarchy": state["hierarchy"],
            }
        )
        response = self._model.invoke(request)

        if response.text().strip().lower() == "yes":
            self.logger.info("'%s' presented", state["element_request"])
            return state
        else:
            self.logger.warning(state)
            raise LookupError()

    def _get_element_info(self, state: AgentState) -> AgentState:
        state["messages"] = self._return_element_info_prompt_template.invoke(
            {
                "screen_element": state["element_request"],
                "hierarchy": without_fields(state["hierarchy"], ["bounds"]),
                "format_instructions": self._output_parser.get_format_instructions(),
            }
        ).to_messages()  # type: ignore[assignment]
        response = self._model.invoke(state["messages"])
        state["messages"].append(response)  # type: ignore[arg-type]
        state["element"] = self._output_parser.parse(response.text())
        return state

    def _find_another_xpath(self, state: AgentState) -> AgentState:
        state["messages"].append(
            "Come up with another xpath, this one doesn't work. "
            "Return only the xpath string in the response!!!"
        )  # type: ignore[arg-type]
        response = self._model.invoke(state["messages"])
        state["messages"].append(response)  # type: ignore[arg-type]
        state["element"]["xpath"] = response.text()
        return state

    def _only_one_element_with_this_xpath(self, state: AgentState) -> str:
        xpath = state["element"]["xpath"]
        try:
            elements = len(self._device.xpath(xpath).all())
        except XPathError:
            elements = 0

        if elements == 1:
            self.logger.info(f"'Single element with xpath = {xpath}")
            return END
        else:
            self.logger.info(f"Retry: {elements} with xpath = {xpath}")
            return "find_another_xpath"

    def find_element_info(self, request: str) -> dict[str, object]:
        result = self._graph.invoke({"element_request": request})
        return {k: v for k, v in result.items() if k != "messages"}
