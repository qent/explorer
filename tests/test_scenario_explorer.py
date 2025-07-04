from typing import cast

import pytest
from langchain_core.language_models import BaseChatModel

from explorer.scenario_explorer import (
    ActionType,
    ExplorerState,
    Scenario,
    ScenarioExplorer,
    Step,
)


class FakeSelector:
    def __init__(self, device: "FakeDevice", xpath: str) -> None:
        self._device = device
        self._xpath = xpath

    def click(self) -> None:
        self._device.clicked.append(self._xpath)


class FakeDevice:
    def __init__(self) -> None:
        self.clicked: list[str] = []
        self.sent_keys: list[str] = []
        self.pressed: list[str] = []
        self.stopped = False

    def xpath(self, xpath: str) -> "FakeSelector":
        from uiautomator2 import XPathElementNotFoundError  # type: ignore[import-untyped]  # isort: skip

        if xpath == "//notfound":
            raise XPathElementNotFoundError("not found")
        return FakeSelector(self, xpath)

    def send_keys(self, text: str) -> None:
        self.sent_keys.append(text)

    def press(self, key: str) -> None:
        self.pressed.append(key)

    def stop_uiautomator(self) -> None:
        self.stopped = True


class FakeNavigator:
    def __init__(
        self, model: object, device: FakeDevice
    ) -> None:  # noqa: D401 - unused
        self.full_hierarchy = "<hierarchy/>"

    def find_element_info(self, request: str) -> dict[str, object]:
        if request == "missing":
            raise LookupError()
        return {"element": {"xpath": f"//{request}"}}


def test_explore(monkeypatch: pytest.MonkeyPatch) -> None:
    device = FakeDevice()
    monkeypatch.setattr(
        "explorer.scenario_explorer.uiautomator2.connect", lambda: device
    )
    monkeypatch.setattr("explorer.scenario_explorer.ElementNavigator", FakeNavigator)
    monkeypatch.setattr("explorer.scenario_explorer.sleep", lambda _: None)

    scenario = Scenario(
        steps=[
            Step(element="btn1", data=None, action=ActionType.CLICK),
            Step(element="home", data=None, action=ActionType.PRESS_KEY),
            Step(element="bad", data=None, action=ActionType.PRESS_KEY),
            Step(element="input", data="hello", action=ActionType.TEXT_INPUT),
            Step(element="missing", data=None, action=ActionType.CLICK),
            Step(element="notfound", data=None, action=ActionType.CLICK),
        ]
    )
    explorer = ScenarioExplorer(model=cast(BaseChatModel, object()))
    state = cast(ExplorerState, {"user_scenario": scenario})
    result = explorer._explore(state)
    trace = result["trace"]

    assert device.stopped
    assert device.clicked == ["//btn1", "//input"]
    assert device.pressed == ["home"]
    assert device.sent_keys == ["hello"]
    assert trace[0]["type"] == ActionType.CLICK
    assert trace[1]["type"] == ActionType.PRESS_KEY
    assert trace[2]["type"] == "INTERRUPTION"
    assert trace[2]["data"] == "InvalidKeyError"
    assert trace[3]["type"] == ActionType.TEXT_INPUT
    assert trace[4]["type"] == "INTERRUPTION"
    assert trace[4]["data"] == "ElementNotFoundError"
    assert trace[5]["type"] == "INTERRUPTION"
    assert trace[5]["data"] == "XPathElementNotFoundError"
