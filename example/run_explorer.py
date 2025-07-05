"""Command line interface for running ``ScenarioExplorer`` with multiple LLMs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from explorer.scenario_explorer import ScenarioExplorer

# Token pricing (per one million tokens)
COSTS: dict[str, dict[str, float]] = {
    "haiku": {"input": 0.80, "output": 4.0},
    "4.1-mini": {"input": 0.40, "output": 1.60},
    "v3": {"input": 0.27, "output": 1.10},
}


def main() -> None:
    """Run ScenarioExplorer with the provided scenario file."""
    parser = argparse.ArgumentParser(
        description="Run ScenarioExplorer using a selected model"
    )
    parser.add_argument(
        "--token",
        help=(
            "LLM API token"
        ),
        default=None,
    )
    parser.add_argument(
        "scenario_file",
        type=Path,
        help="Path to scenario text file",
    )
    parser.add_argument(
        "--api-url",
        dest="api_url",
        help="Custom API URL",
        default=None,
    )
    parser.add_argument(
        "--model",
        choices=["haiku", "4.1-mini", "v3"],
        default="haiku",
        help="Model to use: haiku (Anthropic), 4.1-mini (OpenAI) or v3 (Deepseek)",
    )
    args = parser.parse_args()

    scenario = args.scenario_file.read_text(encoding="utf-8")

    model: BaseChatModel
    if args.model == "haiku":
        model = ChatAnthropic(
            model_name="claude-3-5-haiku-latest",
            api_key=args.token or os.getenv("ANTHROPIC_API_KEY"),
            base_url=args.api_url,
            temperature=0.0,
            max_tokens_to_sample=8000,
            timeout=None,
            stop=None,
        )
        http_client_without_ssl_verification = httpx.Client(verify=False)
        model._client._client = http_client_without_ssl_verification
    elif args.model == "4.1-mini":
        model = ChatOpenAI(
            model="gpt-4.1-mini",
            api_key=args.token or os.getenv("OPENAI_API_KEY"),
            base_url=args.api_url,
            temperature=0.0,
        )
    else:  # v3
        model = ChatOpenAI(
            model="deepseek-chat",
            api_key=args.token or os.getenv("DEEPSEEK_API_KEY"),
            base_url=args.api_url or "https://api.deepseek.com",
            temperature=0.0,
        )

    explorer = ScenarioExplorer(model)
    with get_usage_metadata_callback() as cb:
        result = explorer.explore(scenario)

    usage = cb.usage_metadata
    input_tokens = sum(v.get("input_tokens", 0) for v in usage.values())
    output_tokens = sum(v.get("output_tokens", 0) for v in usage.values())
    cost_info = COSTS[args.model]
    input_cost = input_tokens / 1_000_000 * cost_info["input"]
    output_cost = output_tokens / 1_000_000 * cost_info["output"]
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
