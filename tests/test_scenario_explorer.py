from explorer.scenario_explorer import ActionType, Scenario, ScenarioExplorer, Step


class FakeSelector:
    def __init__(self, device, xpath: str) -> None:
        self._device = device
        self._xpath = xpath

    def click(self) -> None:
        self._device.clicked.append(self._xpath)


class FakeDevice:
    def __init__(self):
        self.clicked: list[str] = []
        self.sent_keys: list[str] = []
        self.stopped = False

    def xpath(self, xpath: str):
        from explorer.scenario_explorer import XPathElementNotFoundError

        if xpath == "//notfound":
            raise XPathElementNotFoundError("not found")
        return FakeSelector(self, xpath)

    def send_keys(self, text: str) -> None:
        self.sent_keys.append(text)

    def stop_uiautomator(self) -> None:
        self.stopped = True


class FakeNavigator:
    def __init__(self, model, device) -> None:  # noqa: D401 - unused
        self.full_hierarchy = "<hierarchy/>"

    def find_element_info(self, request: str) -> dict[str, object]:
        if request == "missing":
            raise LookupError()
        return {"element": {"xpath": f"//{request}"}}


def test_explore(monkeypatch):
    device = FakeDevice()
    monkeypatch.setattr(
        "explorer.scenario_explorer.uiautomator2.connect", lambda: device
    )
    monkeypatch.setattr("explorer.scenario_explorer.ElementNavigator", FakeNavigator)
    monkeypatch.setattr("explorer.scenario_explorer.sleep", lambda _: None)

    scenario = Scenario(
        steps=[
            Step(element="btn1", action=ActionType.CLICK),
            Step(element="input", action=ActionType.TEXT_INPUT, data="hello"),
            Step(element="missing", action=ActionType.CLICK),
            Step(element="notfound", action=ActionType.CLICK),
        ]
    )
    explorer = ScenarioExplorer(model=object())
    state = {"user_scenario": scenario}
    result = explorer._explore(state)
    trace = result["trace"]

    assert device.stopped
    assert device.clicked == ["//btn1", "//input"]
    assert device.sent_keys == ["hello"]
    assert trace[0]["type"] == ActionType.CLICK
    assert trace[1]["type"] == ActionType.TEXT_INPUT
    assert trace[2]["type"] == "INTERRUPTION"
    assert trace[2]["data"] == "ElementNotFoundError"
    assert trace[3]["type"] == "INTERRUPTION"
    assert trace[3]["data"] == "XPathElementNotFoundError"
