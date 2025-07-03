"""Command line interface for running ScenarioExplorer with Anthropic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from langchain_community.chat_models import ChatAnthropic

from explorer.scenario_explorer import ScenarioExplorer


def main() -> None:
    """Run ScenarioExplorer with the provided scenario file."""
    parser = argparse.ArgumentParser(
        description="Run ScenarioExplorer using Claude 3.5 Haiku"
    )
    parser.add_argument("token", help="Anthropic API token")
    parser.add_argument("scenario_file", type=Path, help="Path to scenario text file")
    args = parser.parse_args()

    scenario = args.scenario_file.read_text(encoding="utf-8")

    model = ChatAnthropic(
        model_name="claude-3-5-haiku-latest",
        anthropic_api_key=args.token,
        temperature=0.0,
        max_tokens=8000,
    )

    explorer = ScenarioExplorer(model)
    result = explorer.explore(scenario)

    output_path = Path.cwd() / "explore_result.json"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
