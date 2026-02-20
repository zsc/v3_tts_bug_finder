from __future__ import annotations

import argparse
import pathlib

from .exporter import export_cases
from .report_html import write_html_report
from .runner import run_search


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tts_bug_finder", add_help=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run search (seeds→mutate→score→dedupe→store)")
    run_p.add_argument("--db", default="artifacts/bugs.sqlite")
    run_p.add_argument("--artifacts", default="artifacts")
    run_p.add_argument("--budget", type=int, default=500, help="Max total evaluations")
    run_p.add_argument("--budget-accepted", type=int, default=100, help="Stop after N accepted")
    run_p.add_argument("--concurrency", type=int, default=8)
    run_p.add_argument("--time-limit-sec", type=float, default=0.0, help="0 means no limit")
    run_p.add_argument("--tts", choices=["dummy", "macos_say", "http"], default="dummy")
    run_p.add_argument("--asr", choices=["dummy", "whisper_cli", "http"], default="dummy")
    run_p.add_argument("--llm", choices=["none", "dummy", "http"], default="none")
    run_p.add_argument("--enable-llm", action="store_true")
    run_p.add_argument("--voice", default=None)
    run_p.add_argument("--min-plausibility", type=float, default=0.7)
    run_p.add_argument("--min-cer", type=float, default=0.35)
    run_p.add_argument("--min-wer", type=float, default=0.40)
    run_p.add_argument("--min-critical", type=float, default=0.8)
    run_p.add_argument("--mutate", action=argparse.BooleanOptionalAction, default=True)
    run_p.add_argument("--random-seed", type=int, default=1337)

    exp_p = sub.add_parser("export", help="Export cases from SQLite")
    exp_p.add_argument("--db", default="artifacts/bugs.sqlite")
    exp_p.add_argument("--out", default="artifacts/exports/export.jsonl")
    exp_p.add_argument("--format", choices=["jsonl"], default="jsonl")
    exp_p.add_argument("--status", default="accepted")

    rep_p = sub.add_parser("report", help="Generate a single static HTML report (audio + GT + ASR)")
    rep_p.add_argument("--db", nargs="+", default=["artifacts/bugs.sqlite"])
    rep_p.add_argument("--out", default="artifacts/report.html")
    rep_p.add_argument("--status", default="accepted")
    rep_p.add_argument("--limit", type=int, default=0, help="0 means no limit")
    rep_p.add_argument("--bundle-audio", action=argparse.BooleanOptionalAction, default=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "run":
        run_search(
            db_path=pathlib.Path(args.db),
            artifacts_dir=pathlib.Path(args.artifacts),
            budget_total_eval=args.budget,
            budget_accepted=args.budget_accepted,
            concurrency=args.concurrency,
            time_limit_sec=args.time_limit_sec,
            tts_kind=args.tts,
            asr_kind=args.asr,
            llm_kind=args.llm,
            enable_llm=args.enable_llm,
            voice=args.voice,
            mutate=args.mutate,
            random_seed=args.random_seed,
            thresholds={
                "min_plausibility": args.min_plausibility,
                "min_cer": args.min_cer,
                "min_wer": args.min_wer,
                "min_critical": args.min_critical,
            },
        )
        return 0

    if args.cmd == "export":
        export_cases(
            db_path=pathlib.Path(args.db),
            out_path=pathlib.Path(args.out),
            fmt=args.format,
            status=args.status,
        )
        return 0

    if args.cmd == "report":
        write_html_report(
            db_paths=[pathlib.Path(p) for p in args.db],
            out_path=pathlib.Path(args.out),
            status=args.status,
            limit=int(args.limit),
            bundle_audio=bool(args.bundle_audio),
        )
        return 0

    parser.error(f"Unknown command: {args.cmd}")
    return 2
