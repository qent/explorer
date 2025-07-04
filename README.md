# Explorer

Explorer is a toolkit for automating interaction scenarios with Android applications. It combines **LangChain**, **LangGraph**, and **uiautomator2** to interpret natural language instructions, locate UI elements on a connected device and execute them step-by-step.

## Features

- **Scenario parsing** – converts a free form description of a scenario into structured steps using a language model.
- **Element navigation** – analyses an Android view hierarchy and finds elements by name or description using a language model.
- **Scenario execution** – executes parsed steps against a real device using `uiautomator2` and collects action traces.
- **Device key press** – allows pressing hardware and soft keys during exploration. Supported names: `home`, `back`, `left`, `right`, `up`, `down`, `center`, `menu`, `search`, `enter`, `delete`, `recent`, `volume_up`, `volume_down`, `volume_mute`, `camera`, `power`.

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
pip install git+https://github.com/qent/explorer.git
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

## Example

An example CLI is provided in `example/run_explorer.py`. Pass the path to a
scenario file and optionally your Anthropic API token. A custom API URL can be
provided with the optional `--api-url` flag. When `--token` is omitted the
script falls back to the value of the `ANTHROPIC_API_KEY` environment
variable:

```bash
python example/run_explorer.py \
    --scenario-file /path/to/scenario.txt \
    --token <ANTHROPIC_TOKEN> \
    --api-url https://example.com/v1
```

The script runs the scenario against the currently connected emulator or device
and writes the formatted results to `explore_result.json` in the working
directory.

## Extending the project

This repository favours modern, explicit Python. Follow these principles when contributing:

- Always include type hints for all public functions and methods.
- Keep modules small and focused.
- Document new functions and classes with docstrings.
- Prefer pure functions and clear naming.
- Avoid long argument lists by introducing small data classes.
- Validate data with `pydantic` or dataclasses.
- Write tests for new behaviour using `pytest`.
- Format code with `black` and `isort`, run `ruff` and `mypy` before committing.


