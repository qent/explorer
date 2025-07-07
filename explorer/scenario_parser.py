from __future__ import annotations

from pathlib import Path
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from explorer.models import Scenario
from explorer.utils import get_file_content

# mypy: ignore-errors


class ScenarioParser:
    """Parse a textual request into a :class:`Scenario`."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model
        self._parser = PydanticOutputParser(pydantic_object=Scenario)
        prompt_path = (
            Path(__file__).parent / "prompts" / "extract_step_by_step_scenario.md"
        )
        template_str = get_file_content(str(prompt_path))
        self._prompt_template = PromptTemplate.from_template(template_str)

    def parse(self, request: str) -> Scenario:
        """Return a scenario parsed from ``request``."""
        prompt = self._prompt_template.invoke(
            {
                "scenario": request,
                "format_instructions": self._parser.get_format_instructions(),
            }
        )
        response = self._model.invoke(prompt)
        scenario = cast(Scenario, self._parser.parse(response.text()))
        return scenario
