"""Command line interface for running ScenarioExplorer with Anthropic."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks import get_usage_metadata_callback

from explorer.scenario_explorer import ScenarioExplorer

# Token pricing (per one million tokens)
INPUT_COST_PER_M_TOKEN = 0.80
OUTPUT_COST_PER_M_TOKEN = 4.0


def main() -> None:
    """Run ScenarioExplorer with the provided scenario file."""
    parser = argparse.ArgumentParser(
        description="Run ScenarioExplorer using Claude 3.5 Haiku"
    )
    parser.add_argument(
        "--token",
        help=(
            "Anthropic API token. Defaults to the value of the ANTHROPIC_API_KEY"
            " environment variable."
        ),
        default=os.getenv("ANTHROPIC_API_KEY"),
    )
    parser.add_argument(
        "--scenario-file",
        type=Path,
        required=True,
        help="Path to scenario text file",
    )
    parser.add_argument(
        "--api-url",
        dest="api_url",
        help="Custom Anthropic API URL",
        default=None,
    )
    args = parser.parse_args()

    scenario = args.scenario_file.read_text(encoding="utf-8")

    model = ChatAnthropic(
        model_name="claude-3-5-haiku-latest",
        api_key=args.token,
        base_url=args.api_url,
        temperature=0.0,
        max_tokens_to_sample=8000,
    )
    http_client_without_ssl_verification = httpx.Client(verify=False)
    model._client._client = http_client_without_ssl_verification

    explorer = ScenarioExplorer(model)
    with get_usage_metadata_callback() as cb:
        result = explorer.explore(scenario)

    usage = cb.usage_metadata
    input_tokens = sum(v.get("input_tokens", 0) for v in usage.values())
    output_tokens = sum(v.get("output_tokens", 0) for v in usage.values())
    input_cost = input_tokens / 1_000_000 * INPUT_COST_PER_M_TOKEN
    output_cost = output_tokens / 1_000_000 * OUTPUT_COST_PER_M_TOKEN
    total_tokens = input_tokens + output_tokens
    total_cost = input_cost + output_cost

    output_path = Path.cwd() / "explore_result.json"
    output_path.write_text(
        json.dumps([frame.to_dict() for frame in result], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Results saved to {output_path}")

    print("Token usage:")
    print(f"  input tokens: {input_tokens} cost: ${input_cost:.4f}")
    print(f"  output tokens: {output_tokens} cost: ${output_cost:.4f}")
    print(f"  total tokens: {total_tokens} cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
