"""Command line interface."""
import argparse, json, sys, time
from pathlib import Path
from pydantic import ValidationError
from app.contracts import Bundle
from app.engine import review

def _review(path, output):
    source=Path(path)
    if source.stat().st_size > 2_000_000:
        raise ValueError("Input exceeds 2 MB safety limit; it was not truncated. Split the bundle or extend the documented limit.")
    raw=source.read_text(encoding="utf-8")
    bundle=Bundle.model_validate_json(raw)
    report=review(bundle)
    text=report.model_dump_json(indent=2)
    if output: Path(output).parent.mkdir(parents=True,exist_ok=True); Path(output).write_text(text+"\n",encoding="utf-8")
    else: print(text)
    return 0 if report.status=="PASS" else 1

def main(argv=None):
    p=argparse.ArgumentParser(prog="shodh-review",description="Offline evidence-backed workflow review")
    sub=p.add_subparsers(dest="cmd",required=True)
    r=sub.add_parser("review"); r.add_argument("--input",required=True); r.add_argument("--output")
    e=sub.add_parser("evaluate")
    t=sub.add_parser("test")
    a=sub.add_parser("ablation")
    args=p.parse_args(argv)
    try:
        if args.cmd=="review": return _review(args.input,args.output)
        from app.evaluation import evaluate,ablation
        if args.cmd=="evaluate": print(json.dumps(evaluate(),indent=2)); return 0
        if args.cmd=="ablation": print(json.dumps(ablation(),indent=2)); return 0
        if args.cmd=="test":
            import pytest
            return pytest.main(["-q"])
    except (OSError,ValidationError,json.JSONDecodeError,ValueError) as ex:
        print(f"Input/review error: {ex}",file=sys.stderr); return 2
    except ImportError as ex:
        print(f"Missing development dependency: {ex}. Install requirements.txt.",file=sys.stderr); return 2
    return 2
