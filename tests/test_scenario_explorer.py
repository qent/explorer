from typing import cast

import pytest
from langchain_core.language_models import BaseChatModel

from explorer.models import (
    ActionFrame,
    ActionInfo,
    ActionType,
    ElementInfo,
    ExecutionStatus,
    Scenario,
)
from explorer.scenario_explorer import ExplorerState, ScenarioExplorer

# mypy: ignore-errors


class FakeSelector:
    def __init__(self, device: "FakeDevice", xpath: str) -> None:
        self._device = device
        self._xpath = xpath

    def click(self) -> None:
        self._device.clicked.append(self._xpath)

    def swipe(self, direction: str) -> None:
        self._device.swiped_elements.append((self._xpath, direction))


class FakeDevice:
    def __init__(self) -> None:
        self.clicked: list[str] = []
        self.sent_keys: list[str] = []
        self.pressed: list[str] = []
        self.stopped = False
        self.swiped_elements: list[tuple[str, str]] = []
        self.swiped_screen: list[tuple[int, int, int, int]] = []
        self._size = (1080, 1920)

    def xpath(self, xpath: str) -> "FakeSelector":
        from uiautomator2 import XPathElementNotFoundError  # type: ignore[import-untyped]  # isort: skip

        if xpath == "//notfound":
            raise XPathElementNotFoundError("not found")
        return FakeSelector(self, xpath)

    def window_size(self) -> tuple[int, int]:
        return self._size

    def swipe(self, fx: int, fy: int, tx: int, ty: int) -> None:
        self.swiped_screen.append((fx, fy, tx, ty))

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
        actions=[
            ActionInfo(element=ElementInfo(description="btn1"), type=ActionType.CLICK),
            ActionInfo(data="home", type=ActionType.PRESS_KEY),
            ActionInfo(data="bad", type=ActionType.PRESS_KEY),
            ActionInfo(
                element=ElementInfo(description="input"),
                data="hello",
                type=ActionType.TEXT_INPUT,
            ),
            ActionInfo(
                element=ElementInfo(description="missing"), type=ActionType.CLICK
            ),
            ActionInfo(
                element=ElementInfo(description="notfound"), type=ActionType.CLICK
            ),
        ]
    )
    explorer = ScenarioExplorer(model=cast(BaseChatModel, object()))
    state = cast(ExplorerState, {"user_scenario": scenario})
    result = explorer._explore(state)
    trace = result["trace"]

    assert device.stopped
    assert device.clicked == ["//btn1"]
    assert device.pressed == ["home"]
    assert device.sent_keys == []
    assert trace[0].action.type == ActionType.CLICK
    assert trace[0].action.status == ExecutionStatus.EXECUTED
    assert trace[1].action.type == ActionType.PRESS_KEY
    assert trace[1].action.status == ExecutionStatus.EXECUTED
    assert trace[2].error and trace[2].error.type == "InvalidKeyError"
    assert trace[2].action.status == ExecutionStatus.BROKEN
    # Following actions should remain pending due to early stop
    assert trace[3].action.status == ExecutionStatus.PENDING
    assert trace[4].action.status == ExecutionStatus.PENDING
    assert trace[5].action.status == ExecutionStatus.PENDING


class NoCallNavigator:
    def __init__(
        self, model: object, device: FakeDevice
    ) -> None:  # noqa: D401 - unused
        pass

    def find_element_info(self, request: str) -> dict[str, object]:
        raise AssertionError("Navigator should not be used")


def test_swipe_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    device = FakeDevice()
    monkeypatch.setattr(
        "explorer.scenario_explorer.uiautomator2.connect", lambda: device
    )
    monkeypatch.setattr("explorer.scenario_explorer.ElementNavigator", FakeNavigator)
    monkeypatch.setattr("explorer.scenario_explorer.sleep", lambda _: None)

    scenario = Scenario(
        actions=[
            ActionInfo(
                element=ElementInfo(description="btn"),
                data="left",
                type=ActionType.SWIPE_ELEMENT,
            ),
            ActionInfo(data="up", type=ActionType.SWIPE_SCREEN),
        ]
    )

    explorer = ScenarioExplorer(model=cast(BaseChatModel, object()))
    state = cast(ExplorerState, {"user_scenario": scenario})
    result = explorer._explore(state)
    trace = result["trace"]

    assert trace[0].action.status == ExecutionStatus.EXECUTED
    assert device.swiped_elements == [("//btn", "left")]
    width, height = device.window_size()
    margin = 100
    assert device.swiped_screen == [(width // 2, height - margin, width // 2, margin)]


def test_run_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    device = FakeDevice()
    monkeypatch.setattr(
        "explorer.scenario_explorer.uiautomator2.connect", lambda: device
    )
    monkeypatch.setattr("explorer.scenario_explorer.ElementNavigator", NoCallNavigator)
    monkeypatch.setattr("explorer.scenario_explorer.sleep", lambda _: None)

    trace = [
        ActionFrame(
            screen=None,
            action=ActionInfo(
                element=ElementInfo(description="btn", xpath="//btn"),
                type=ActionType.CLICK,
                status=ExecutionStatus.EXECUTED,
            ),
            error=None,
        ),
        ActionFrame(
            screen=None,
            action=ActionInfo(
                data="home",
                type=ActionType.PRESS_KEY,
                status=ExecutionStatus.EXECUTED,
            ),
            error=None,
        ),
        ActionFrame(
            screen=None,
            action=ActionInfo(
                element=ElementInfo(description="el", xpath="//el"),
                data="right",
                type=ActionType.SWIPE_ELEMENT,
                status=ExecutionStatus.EXECUTED,
            ),
            error=None,
        ),
        ActionFrame(
            screen=None,
            action=ActionInfo(
                data="down",
                type=ActionType.SWIPE_SCREEN,
                status=ExecutionStatus.EXECUTED,
            ),
            error=None,
        ),
    ]

    explorer = ScenarioExplorer(model=cast(BaseChatModel, object()))
    result = explorer.run_trace(trace)

    assert device.clicked == ["//btn"]
    assert device.pressed == ["home"]
    assert device.swiped_elements == [("//el", "right")]
    width, height = device.window_size()
    margin = 100
    assert device.swiped_screen == [(width // 2, margin, width // 2, height - margin)]
    assert result[0].action.status == ExecutionStatus.EXECUTED
