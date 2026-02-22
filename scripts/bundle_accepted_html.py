#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import glob
import html
import json
import pathlib
import re
import shutil
from typing import Any


def _collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _load_cases(patterns: list[str]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for pat in patterns:
        for p in sorted(glob.glob(pat)):
            path = pathlib.Path(p)
            run_dir = path.parent
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    if not isinstance(d, dict):
                        continue
                    d["_src_jsonl"] = str(path)
                    d["_src_run_dir"] = str(run_dir)
                    cases.append(d)
    return cases


def _dedupe_by_ref_text_best_score(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for c in cases:
        ref = _collapse_ws(str(c.get("ref_text") or ""))
        if not ref:
            continue
        prev = best.get(ref)
        if prev is None or _safe_float(c.get("score_total")) > _safe_float(prev.get("score_total")):
            best[ref] = c
    return list(best.values())


def _copy_audio(*, root: pathlib.Path, out_dir: pathlib.Path, case: dict[str, Any]) -> str:
    cid = str(case.get("id") or "").strip()
    if not cid:
        raise RuntimeError("missing case id")
    audio_path = case.get("audio_path_wav")
    if not audio_path:
        raise RuntimeError(f"case {cid} missing audio_path_wav")

    src = pathlib.Path(str(audio_path))
    if not src.is_absolute():
        src = root / src
    if not src.exists():
        raise FileNotFoundError(f"audio not found for {cid}: {src}")

    dst_name = f"{cid}.wav"
    dst = out_dir / dst_name
    if not dst.exists():
        shutil.copyfile(src, dst)
    return dst_name


def _render_html(*, out_dir: pathlib.Path, title: str, cases: list[dict[str, Any]]) -> None:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts: list[str] = []
    parts.append("<!doctype html>")
    parts.append('<html lang="en">')
    parts.append("<head>")
    parts.append('<meta charset="utf-8" />')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1" />')
    parts.append(f"<title>{html.escape(title)}</title>")
    parts.append(
        """
<style>
  :root { color-scheme: light dark; }
  body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 18px; }
  header { position: sticky; top: 0; background: rgba(255,255,255,0.85); backdrop-filter: blur(10px); padding: 10px 12px; border: 1px solid rgba(0,0,0,0.08); border-radius: 12px; z-index: 2; }
  @media (prefers-color-scheme: dark) {
    header { background: rgba(0,0,0,0.35); border-color: rgba(255,255,255,0.10); }
  }
  h1 { font-size: 18px; margin: 0 0 8px 0; }
  .meta { font-size: 12px; opacity: 0.8; display: flex; gap: 12px; flex-wrap: wrap; }
  .controls { margin-top: 10px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  input[type="search"] { width: min(560px, 100%); padding: 8px 10px; border-radius: 10px; border: 1px solid rgba(0,0,0,0.20); background: transparent; }
  button { padding: 7px 10px; border-radius: 10px; border: 1px solid rgba(0,0,0,0.20); background: transparent; cursor: pointer; }
  .list { margin-top: 14px; display: grid; gap: 12px; }
  details.case { border: 1px solid rgba(0,0,0,0.10); border-radius: 12px; overflow: hidden; }
  details.case > summary { list-style: none; cursor: pointer; padding: 10px 12px; display: grid; grid-template-columns: 110px 1fr; gap: 10px; align-items: center; }
  details.case > summary::-webkit-details-marker { display: none; }
  .score { font-variant-numeric: tabular-nums; font-weight: 700; }
  .summary-line { font-size: 13px; display: grid; gap: 4px; }
  .tags { font-size: 12px; opacity: 0.85; }
  .case-body { padding: 12px; border-top: 1px solid rgba(0,0,0,0.08); }
  .top-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 10px; }
  audio { width: min(620px, 100%); }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  .panel { border: 1px solid rgba(0,0,0,0.10); border-radius: 12px; padding: 10px; }
  .panel h3 { margin: 0 0 8px 0; font-size: 13px; opacity: 0.9; }
  pre.text { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", monospace; font-size: 12.5px; line-height: 1.35; }
  .kv { font-size: 12px; opacity: 0.85; display: grid; gap: 2px; }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; border: 1px solid rgba(0,0,0,0.20); font-size: 12px; opacity: 0.9; }
  .filelink { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", monospace; }
</style>
        """.strip()
    )
    parts.append("</head>")
    parts.append("<body>")

    parts.append("<header>")
    parts.append(f"<h1>{html.escape(title)}</h1>")
    parts.append(
        f'<div class="meta"><div><span class="pill">cases</span> <strong id="caseCount">{len(cases)}</strong></div>'
        f"<div><span class='pill'>generated</span> {html.escape(generated_at)}</div>"
        f"<div><span class='pill'>dir</span> <span class='filelink'>{html.escape(str(out_dir))}</span></div>"
        "</div>"
    )
    parts.append(
        """
<div class="controls">
  <input id="q" type="search" placeholder="Search in GT / ASR / tags..." />
  <button id="expandAll">Expand all</button>
  <button id="collapseAll">Collapse all</button>
</div>
        """.strip()
    )
    parts.append("</header>")

    parts.append('<div class="list" id="list">')
    for r in cases:
        cid = str(r.get("id") or "")
        ref = str(r.get("ref_text") or "")
        hyp = str(r.get("hyp_text") or "")
        tags = r.get("tags") or []
        if isinstance(tags, list):
            tag_str = ", ".join(str(t) for t in tags)
        else:
            tag_str = ""
        score = _safe_float(r.get("score_total"))
        cer = _safe_float(r.get("cer"))
        wer = _safe_float(r.get("wer"))
        critical = _safe_float(r.get("critical_error_score"))
        audio_file = str(r.get("_bundle_wav") or "")
        if not audio_file:
            continue

        ref_preview = _collapse_ws(ref.replace("\n", " "))
        if len(ref_preview) > 140:
            ref_preview = ref_preview[:140] + "…"

        searchable = " ".join([cid, tag_str, ref, hyp])
        searchable_attr = html.escape(searchable.replace("\n", " "))

        parts.append(f'<details class="case" data-search="{searchable_attr}">')
        parts.append("<summary>")
        parts.append(f'<div class="score">{score:0.1f}</div>')
        parts.append(
            f'<div class="summary-line"><div>{html.escape(ref_preview)}</div>'
            f'<div class="tags">{html.escape(tag_str)}</div></div>'
        )
        parts.append("</summary>")

        parts.append('<div class="case-body">')
        parts.append('<div class="top-row">')
        parts.append(f'<audio controls preload="none" src="{html.escape(audio_file)}"></audio>')
        parts.append(
            "<div class='kv'>"
            f"<div><strong>id</strong>: {html.escape(cid)}</div>"
            f"<div><strong>score</strong>: {score:0.1f} &nbsp; <strong>cer</strong>: {cer:0.2f} &nbsp; <strong>wer</strong>: {wer:0.2f} &nbsp; <strong>critical</strong>: {critical:0.2f}</div>"
            f"<div><strong>wav</strong>: <span class='filelink'>{html.escape(audio_file)}</span></div>"
            "</div>"
        )
        parts.append("</div>")

        parts.append('<div class="grid">')
        parts.append('<div class="panel">')
        parts.append("<h3>GT (ref_text)</h3>")
        parts.append(f'<pre class="text">{html.escape(ref)}</pre>')
        parts.append("</div>")
        parts.append('<div class="panel">')
        parts.append("<h3>ASR (hyp_text)</h3>")
        parts.append(f'<pre class="text">{html.escape(hyp)}</pre>')
        parts.append("</div>")
        parts.append("</div>")

        parts.append("</div>")
        parts.append("</details>")
    parts.append("</div>")

    parts.append(
        """
<script>
  const q = document.getElementById('q');
  const list = document.getElementById('list');
  const details = () => Array.from(list.querySelectorAll('details.case'));

  function applyFilter() {
    const needle = (q.value || '').trim().toLowerCase();
    let shown = 0;
    for (const el of details()) {
      const hay = (el.getAttribute('data-search') || '').toLowerCase();
      const ok = !needle || hay.includes(needle);
      el.style.display = ok ? '' : 'none';
      if (ok) shown++;
    }
    document.getElementById('caseCount').textContent = String(shown);
  }

  q.addEventListener('input', applyFilter);

  document.getElementById('expandAll').addEventListener('click', () => {
    for (const el of details()) el.open = true;
  });
  document.getElementById('collapseAll').addEventListener('click', () => {
    for (const el of details()) el.open = false;
  });
</script>
        """.strip()
    )

    parts.append("</body></html>")
    (out_dir / "index.html").write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Bundle accepted cases into one directory + a single HTML player page.")
    ap.add_argument(
        "--accepted-jsonl",
        action="append",
        default=[],
        help="Glob for accepted.jsonl (repeatable). Default: artifacts_indextts2_*/accepted.jsonl",
    )
    ap.add_argument("--out", default="indextts2_accepted_bundle", help="Output directory (will be created).")
    ap.add_argument("--title", default="IndexTTS2 Accepted Cases (GT vs ASR + WAV)")
    ap.add_argument("--dedupe-ref", action="store_true", help="Dedupe by ref_text (keep best score_total).")
    ap.add_argument("--limit", type=int, default=0, help="0 means no limit.")
    args = ap.parse_args()

    patterns = args.accepted_jsonl or ["artifacts_indextts2_*/accepted.jsonl"]
    root = pathlib.Path.cwd()
    out_dir = pathlib.Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = _load_cases(patterns)
    if not cases:
        raise SystemExit(f"No cases loaded from patterns: {patterns}")

    if args.dedupe_ref:
        cases = _dedupe_by_ref_text_best_score(cases)

    cases.sort(key=lambda c: _safe_float(c.get("score_total")), reverse=True)
    if args.limit and args.limit > 0:
        cases = cases[: int(args.limit)]

    # Copy audio + attach bundle filename for HTML.
    copied = 0
    for c in cases:
        c["_bundle_wav"] = _copy_audio(root=root, out_dir=out_dir, case=c)
        copied += 1

    # Write a small manifest for programmatic use.
    manifest = out_dir / "cases.jsonl"
    with manifest.open("w", encoding="utf-8") as f:
        for c in cases:
            row = {
                "id": c.get("id"),
                "score_total": c.get("score_total"),
                "cer": c.get("cer"),
                "wer": c.get("wer"),
                "critical_error_score": c.get("critical_error_score"),
                "tags": c.get("tags"),
                "ref_text": c.get("ref_text"),
                "hyp_text": c.get("hyp_text"),
                "wav": c.get("_bundle_wav"),
                "src_jsonl": c.get("_src_jsonl"),
                "src_audio_path_wav": c.get("audio_path_wav"),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    _render_html(out_dir=out_dir, title=str(args.title), cases=cases)
    print(f"OK: wrote {out_dir}/index.html with {len(cases)} cases; copied {copied} wavs; manifest={manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

