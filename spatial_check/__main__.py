"""Raw files are claims, never automatically confirmed. Demo has fixed inputs."""
import argparse
import json
import sys
from .engine import evaluate
from .explanation import format_result
from .json_io import load


def main() -> int:
    parser = argparse.ArgumentParser(description="Rectangular 2D check; no automatic measurements.")
    parser.add_argument("request", nargs="?")
    parser.add_argument("evidence_claim", nargs="?")
    parser.add_argument("--demo", choices=["fits", "clearance_conflict", "unverified"])
    parser.add_argument("--text", action="store_true")
    args = parser.parse_args()
    if args.demo:
        if args.request or args.evidence_claim:
            parser.error("Demo does not accept external data.")
        from .demo import run_demo
        result = run_demo(args.demo)
        print(("DEMO ONLY — SYNTHETIC DATA\n" + result["status"]) if args.text
              else json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result["status"] == "UNVERIFIED" else 1 if result["status"] == "CONFLICT DETECTED" else 0
    if not args.request or not args.evidence_claim:
        parser.error("Supply request and evidence claim files, or --demo.")
    try:
        request, evidence = load(args.request), load(args.evidence_claim)
    except (OSError, ValueError, RecursionError):
        result = evaluate(None, None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    result = evaluate(request, evidence)
    print(format_result(request, evidence) if args.text else json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] == "UNVERIFIED" else 1 if result["status"] == "CONFLICT DETECTED" else 0


if __name__ == "__main__":
    sys.exit(main())
