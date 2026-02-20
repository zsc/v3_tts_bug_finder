from __future__ import annotations

import base64
import datetime as dt
import html
import json
import pathlib
from typing import Any

from .db import BugDB


def _read_audio_bytes(audio_path_wav: str | None, *, db_path: pathlib.Path) -> bytes | None:
    if not audio_path_wav:
        return None
    p = pathlib.Path(audio_path_wav)
    candidates = [p, db_path.parent / p]
    for c in candidates:
        try:
            if c.exists() and c.is_file():
                return c.read_bytes()
        except Exception:
            continue
    return None


def _parse_statuses(status: str) -> list[str] | None:
    s = (status or "").strip()
    if not s or s.lower() == "all":
        return None
    return [p.strip() for p in s.split(",") if p.strip()]


def _fetch_cases(db_path: pathlib.Path, *, statuses: list[str] | None) -> list[dict[str, Any]]:
    with BugDB(db_path) as db:
        if statuses is None:
            return list(db.iter_cases(status=None))
        out: list[dict[str, Any]] = []
        for st in statuses:
            out.extend(list(db.iter_cases(status=st)))
        return out


def _fmt_tags(tags: Any) -> str:
    if isinstance(tags, list):
        return ", ".join(str(t) for t in tags)
    return ""


def write_html_report(
    *,
    db_paths: list[pathlib.Path],
    out_path: pathlib.Path,
    status: str,
    limit: int,
    bundle_audio: bool,
) -> None:
    statuses = _parse_statuses(status)
    cases: list[dict[str, Any]] = []
    for db_path in db_paths:
        rows = _fetch_cases(db_path, statuses=statuses)
        for r in rows:
            r = dict(r)
            r["_source_db"] = str(db_path)
            cases.append(r)

    cases.sort(key=lambda r: float(r.get("score_total") or 0.0), reverse=True)
    if limit and limit > 0:
        cases = cases[:limit]

    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    parts: list[str] = []
    parts.append("<!doctype html>")
    parts.append('<html lang="en">')
    parts.append("<head>")
    parts.append('<meta charset="utf-8" />')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1" />')
    parts.append("<title>TTS Bug Finder Report</title>")
    parts.append(
        """
<style>
  :root { color-scheme: light dark; }
  body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 18px; }
  header { position: sticky; top: 0; background: rgba(255,255,255,0.85); backdrop-filter: blur(10px); padding: 10px 12px; border: 1px solid rgba(0,0,0,0.08); border-radius: 12px; }
  @media (prefers-color-scheme: dark) {
    header { background: rgba(0,0,0,0.35); border-color: rgba(255,255,255,0.10); }
  }
  h1 { font-size: 18px; margin: 0 0 8px 0; }
  .meta { font-size: 12px; opacity: 0.8; display: flex; gap: 12px; flex-wrap: wrap; }
  .controls { margin-top: 10px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  input[type="search"] { width: min(520px, 100%); padding: 8px 10px; border-radius: 10px; border: 1px solid rgba(0,0,0,0.20); background: transparent; }
  button { padding: 7px 10px; border-radius: 10px; border: 1px solid rgba(0,0,0,0.20); background: transparent; cursor: pointer; }
  .list { margin-top: 14px; display: grid; gap: 12px; }
  details.case { border: 1px solid rgba(0,0,0,0.10); border-radius: 12px; overflow: hidden; }
  details.case > summary { list-style: none; cursor: pointer; padding: 10px 12px; display: grid; grid-template-columns: 90px 1fr; gap: 10px; align-items: center; }
  details.case > summary::-webkit-details-marker { display: none; }
  .score { font-variant-numeric: tabular-nums; font-weight: 700; }
  .summary-line { font-size: 13px; display: grid; gap: 4px; }
  .tags { font-size: 12px; opacity: 0.85; }
  .case-body { padding: 12px; border-top: 1px solid rgba(0,0,0,0.08); }
  .top-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 10px; }
  audio { width: min(520px, 100%); }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  .panel { border: 1px solid rgba(0,0,0,0.10); border-radius: 12px; padding: 10px; }
  .panel h3 { margin: 0 0 8px 0; font-size: 13px; opacity: 0.9; }
  pre.text { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; font-size: 12.5px; line-height: 1.35; }
  .kv { font-size: 12px; opacity: 0.85; display: grid; gap: 2px; }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; border: 1px solid rgba(0,0,0,0.20); font-size: 12px; opacity: 0.9; }
</style>
        """.strip()
    )
    parts.append("</head>")
    parts.append("<body>")

    db_list = ", ".join(html.escape(str(p)) for p in db_paths)
    parts.append("<header>")
    parts.append("<h1>TTS Bug Finder Report</h1>")
    parts.append(
        f'<div class="meta"><div><span class="pill">cases</span> <strong id="caseCount">{len(cases)}</strong></div>'
        f"<div><span class='pill'>generated</span> {html.escape(generated_at)}</div>"
        f"<div><span class='pill'>db</span> {db_list}</div>"
        f"<div><span class='pill'>status</span> {html.escape(status or 'all')}</div></div>"
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
    for i, r in enumerate(cases, start=1):
        cid = str(r.get("id") or "")
        ref = str(r.get("ref_text") or "")
        hyp = str(r.get("hyp_text") or "")
        tags = r.get("tags") or []
        tag_str = _fmt_tags(tags)
        score = float(r.get("score_total") or 0.0)
        cer = float(r.get("cer") or 0.0)
        wer = float(r.get("wer") or 0.0)
        critical = float(r.get("critical_error_score") or 0.0)
        seed_id = r.get("seed_id") or ""
        mutation_trace = r.get("mutation_trace") or ""
        source_db = r.get("_source_db") or ""
        audio_path = r.get("audio_path_wav")

        audio_src = ""
        audio_note = ""
        if bundle_audio:
            audio_bytes = _read_audio_bytes(audio_path, db_path=pathlib.Path(source_db))
            if audio_bytes:
                b64 = base64.b64encode(audio_bytes).decode("ascii")
                audio_src = f"data:audio/wav;base64,{b64}"
            else:
                audio_note = "audio missing"
        else:
            if audio_path:
                audio_src = html.escape(str(audio_path))
            else:
                audio_note = "audio missing"

        ref_preview = ref.replace("\n", " ").strip()
        if len(ref_preview) > 140:
            ref_preview = ref_preview[:140] + "…"

        searchable = " ".join(
            [
                cid,
                tag_str,
                ref,
                hyp,
                str(seed_id),
                str(mutation_trace),
                str(source_db),
            ]
        )
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
        if audio_src:
            parts.append(f'<audio controls preload="none" src="{audio_src}"></audio>')
        if audio_note:
            parts.append(f"<div class='kv'>{html.escape(audio_note)}</div>")
        parts.append(
            "<div class='kv'>"
            f"<div><strong>id</strong>: {html.escape(cid)}</div>"
            f"<div><strong>score</strong>: {score:0.1f} &nbsp; <strong>cer</strong>: {cer:0.2f} &nbsp; <strong>wer</strong>: {wer:0.2f} &nbsp; <strong>critical</strong>: {critical:0.2f}</div>"
            f"<div><strong>seed_id</strong>: {html.escape(str(seed_id))}</div>"
            f"<div><strong>mutation_trace</strong>: {html.escape(str(mutation_trace))}</div>"
            f"<div><strong>audio_path_wav</strong>: {html.escape(str(audio_path or ''))}</div>"
            f"<div><strong>db</strong>: {html.escape(str(source_db))}</div>"
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

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {out_path} ({len(cases)} cases, bundle_audio={bundle_audio})")

