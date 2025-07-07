from typing import Any

import pytest

from explorer.models import ActionInfo, ActionType, ElementInfo, Scenario
from explorer.scenario_parser import ScenarioParser

# mypy: ignore-errors


class FakeResponse:
    def __init__(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text


class FakeModel:
    def __init__(self) -> None:
        self.last_request: Any | None = None

    def invoke(self, request: Any) -> FakeResponse:
        self.last_request = request
        return FakeResponse("response")


class FakeParser:
    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario

    def get_format_instructions(self) -> str:
        return "instructions"

    def parse(self, text: str) -> Scenario:
        assert text == "response"
        return self.scenario


class FakePrompt:
    def __init__(self, template: str) -> None:  # noqa: D401 - unused
        pass

    def invoke(self, values: dict[str, object]) -> str:  # noqa: D401 - unused
        return "prompt"


def test_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    scenario = Scenario(
        actions=[
            ActionInfo(element=ElementInfo(description="btn"), type=ActionType.CLICK)
        ]
    )

    fake_parser = FakeParser(scenario)
    monkeypatch.setattr(
        "explorer.scenario_parser.PydanticOutputParser",
        lambda pydantic_object: fake_parser,
    )
    monkeypatch.setattr(
        "explorer.scenario_parser.PromptTemplate",
        type(
            "PromptTemplate",
            (),
            {"from_template": lambda template: FakePrompt(template)},
        ),
    )

    model = FakeModel()
    parser = ScenarioParser(model)
    result = parser.parse("open app")

    assert model.last_request == "prompt"
    assert result == scenario
