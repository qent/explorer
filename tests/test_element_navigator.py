from typing import cast

from langgraph.constants import END  # type: ignore[import-not-found]
from uiautomator2.xpath import XPathError  # type: ignore[import-not-found]

from explorer.element_navigator import AgentState, ElementNavigator


class FakeXPath:
    def __init__(self, elements: int, raise_error: bool = False) -> None:
        self._elements = elements
        self._raise_error = raise_error

    def all(self) -> list[object]:
        if self._raise_error:
            raise XPathError("fail")
        return [object()] * self._elements


class FakeDevice:
    def __init__(self, elements: int, raise_error: bool = False) -> None:
        self._elements = elements
        self._raise_error = raise_error

    def xpath(self, xpath: str) -> FakeXPath:
        return FakeXPath(self._elements, self._raise_error)


def make_nav(elements: int, raise_error: bool = False) -> ElementNavigator:
    nav = ElementNavigator.__new__(ElementNavigator)
    nav._device = FakeDevice(elements, raise_error)
    nav.logger = ElementNavigator.logger
    return nav


def test_only_one_element_returns_end() -> None:
    nav = make_nav(1)
    state = cast(AgentState, {"element": {"xpath": "//foo"}})
    assert nav._only_one_element_with_this_xpath(state) == END


def test_multiple_elements_requests_retry() -> None:
    nav = make_nav(2)
    state = cast(AgentState, {"element": {"xpath": "//foo"}})
    assert nav._only_one_element_with_this_xpath(state) == "find_another_xpath"


def test_xpath_error_treated_as_retry() -> None:
    nav = make_nav(1, True)
    state = cast(AgentState, {"element": {"xpath": "//foo"}})
    assert nav._only_one_element_with_this_xpath(state) == "find_another_xpath"
