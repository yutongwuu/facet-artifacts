"""Run python -m emoemg --help."""
import argparse
import json
from pathlib import Path
from .pipeline import Config, train, simulate, replay


def main():
    parser = argparse.ArgumentParser(description="FACET action classification baseline")
    sub = parser.add_subparsers(dest="command", required=True)
    sim = sub.add_parser("simulate")
    sim.add_argument("--output", required=True)
    sim.add_argument("--config")
    fit = sub.add_parser("train")
    fit.add_argument("--train", nargs="+", required=True)
    fit.add_argument("--test", nargs="+", required=True)
    fit.add_argument("--config", required=True)
    fit.add_argument("--output", required=True)
    infer = sub.add_parser("replay")
    infer.add_argument("--model", required=True)
    infer.add_argument("--input", required=True)
    infer.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if args.command == "replay":
            replay(args.model, args.input, args.output)
        else:
            config = Config(**json.loads(Path(args.config).read_text())) if args.config else Config()
            if args.command == "simulate":
                simulate(args.output, config)
                print("SYNTHETIC data generated; not physiological evidence.")
            else:
                _, report = train(args.train, args.test, config, args.output)
                print(json.dumps(report, indent=2))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
