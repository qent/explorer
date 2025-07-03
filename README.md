# Explorer

Explorer is a toolkit for automating interaction scenarios with Android applications. It combines **LangChain**, **LangGraph**, and **uiautomator2** to interpret natural language instructions, locate UI elements on a connected device and execute them step-by-step.

## Features

- **Scenario parsing** – converts a free form description of a scenario into structured steps using a language model.
- **Element navigation** – analyses an Android view hierarchy and finds elements by name or description using a language model.
- **Scenario execution** – executes parsed steps against a real device using `uiautomator2` and collects action traces.

## Project layout

```
explorer/
│   action_frame.py        # typed dictionary describing a single action
│   element_navigator.py   # logic for locating UI elements using an LLM
│   scenario_explorer.py   # high level scenario execution engine
│   viewnode.py            # helpers to parse Android XML hierarchy
│   utils.py               # small utilities
│   prompts/
│       extract_step_by_step_scenario.md  # prompt template for scenario parser
```

## Requirements

- Python 3.11+
- Android device available via [`uiautomator2`](https://github.com/openatx/uiautomator2)
- Python packages listed in `requirements.txt` (install with `pip -r requirements.txt`)

Development utilities are also included in `requirements.txt`.

## Installation

The library can be installed directly from GitHub:

```bash
pip install git+https://github.com/<username>/explorer.git
```

For development install optional dependencies as well:

```bash
pip install -r requirements.txt
```

## Usage

The main entry point is `ScenarioExplorer`. Provide it with a `BaseChatModel` implementation from LangChain and run `explore()` with a natural language scenario:

```python
from langchain.chat_models import ChatOpenAI  # or any other model
from explorer.scenario_explorer import ScenarioExplorer

model = ChatOpenAI()
explorer = ScenarioExplorer(model)
result = explorer.explore("Open the app, log in and check my account balance")
for frame in result:
    print(frame)
```

Each item in `result` is an `ActionFrame` describing the action performed, including element metadata and optional input text. Interruptions such as missing elements are also recorded.

## Extending the project

This repository favours modern, explicit Python. Follow these principles when contributing:

- Always include type hints for all public functions and methods.
- Keep modules small and focused.
- Document new functions and classes with docstrings.
- Validate data with `pydantic` or dataclasses.
- Write tests for new behaviour using `pytest`.
- Format code with `black` and `isort`, run `ruff` and `mypy` before committing.


