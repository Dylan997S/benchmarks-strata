"""Run one quality round against an already-running local service."""
import argparse
from pathlib import Path
import benchmark

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, required=True)
parser.add_argument("--label", required=True)
parser.add_argument("--round", type=int, choices=(1, 2), required=True)
args = parser.parse_args()
if not args.label.replace("-", "").replace("_", "").isalnum():
    parser.error("label must contain only letters, digits, hyphens or underscores")
benchmark.PORT = args.port
benchmark.run_round(args.label, args.round)
