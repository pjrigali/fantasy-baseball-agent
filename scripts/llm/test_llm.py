"""
Description: Tests the configured LLM provider by sending a simple fantasy
             baseball prompt and printing the response. Use this to confirm
             your LLM is connected correctly after updating config.ini.
Source Data: config.ini [llm] section.
Outputs: Console response from the configured LLM provider.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.llm import get_llm, is_configured, _DEFAULT_MODELS


def main():
    parser = argparse.ArgumentParser(description="Test the configured LLM provider.")
    parser.add_argument("--provider", type=str, default=None,
                        help="Override provider (anthropic|openai|google|ollama).")
    parser.add_argument("--model",    type=str, default=None,
                        help="Override model name.")
    parser.add_argument("--prompt",   type=str,
                        default="In one sentence, what is the most important category to win in a 5x5 H2H fantasy baseball league?",
                        help="Custom test prompt.")
    args = parser.parse_args()

    if not is_configured() and not args.provider:
        print("\nNo LLM configured in config.ini.")
        print("Add the following to your config.ini:\n")
        print("  [llm]")
        print("  provider = anthropic   # or openai, google, ollama")
        print("  model    = claude-sonnet-4-5\n")
        print("Supported providers and default models:")
        for p, m in _DEFAULT_MODELS.items():
            print(f"  {p:<12} → {m}")
        return

    print(f"\nConnecting to LLM...")
    try:
        llm = get_llm(provider=args.provider, model=args.model)
        print(f"Provider : {llm.provider}")
        print(f"Model    : {llm.model}")
        print(f"\nPrompt   : {args.prompt}")
        print(f"\nResponse :")
        print("-" * 60)
        response = llm.complete(args.prompt)
        print(response)
        print("-" * 60)
        print("\nLLM connection successful.")
    except ImportError as e:
        print(f"\nMissing SDK: {e}")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
