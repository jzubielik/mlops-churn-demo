"""Static report site generator (GitHub Pages) for the churn demo.

Assembles a single bundle into ``site/index.html``:
  * a metrics table from ``metrics.json`` (the latest model result),
  * a link/embed of the drift report ``drift_report.html`` (Evidently),
  * model and data cards (``docs/model_card.md``, ``docs/data_card.md``) and
    the architecture (``docs/architecture.md``).

No external dependencies — a lightweight Markdown→HTML converter (headings, lists,
tables, paragraphs, code blocks, inline code/bold). Sufficient for our
documents and friendly to a free runner.

Run:
    python scripts/build_site.py
"""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
METRICS = ROOT / "metrics.json"
DRIFT_HTML = ROOT / "drift_report.html"
DOCS = ROOT / "docs"


# --- mini Markdown -> HTML --------------------------------------------------
def _inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    # [label](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def _table(rows: list[str]) -> str:
    cells = [
        [c.strip() for c in r.strip().strip("|").split("|")]
        for r in rows
        if r.strip()
    ]
    if len(cells) < 2:
        return ""
    header, body = cells[0], cells[2:]  # cells[1] = separator
    out = ["<table><thead><tr>"]
    out += [f"<th>{_inline(c)}</th>" for c in header]
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # code blocks ```...```
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip().lower()
            i += 1
            code: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(html.escape(lines[i]))
                i += 1
            i += 1
            if lang == "mermaid":
                # Rendered client-side by mermaid.js (see <script> in TEMPLATE).
                out.append('<pre class="mermaid">' + "\n".join(code) + "</pre>")
            else:
                out.append("<pre><code>" + "\n".join(code) + "</code></pre>")
            continue

        # tables (lines starting with |)
        if line.strip().startswith("|"):
            tbl: list[str] = []
            while i < n and lines[i].strip().startswith("|"):
                tbl.append(lines[i])
                i += 1
            out.append(_table(tbl))
            continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue

        # lists
        if re.match(r"^\s*[-*]\s+", line):
            items: list[str] = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append("<li>" + _inline(re.sub(r"^\s*[-*]\s+", "", lines[i])) + "</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # blank
        if not line.strip():
            i += 1
            continue

        # paragraph
        out.append(f"<p>{_inline(line)}</p>")
        i += 1

    return "\n".join(out)


def _metrics_table() -> str:
    if not METRICS.exists():
        return "<p><em>No metrics.json — run: make train-model.</em></p>"
    data = json.loads(METRICS.read_text(encoding="utf-8"))
    rows = "".join(
        f"<tr><td><code>{html.escape(str(k))}</code></td>"
        f"<td>{html.escape(str(v))}</td></tr>"
        for k, v in data.items()
    )
    head = "<thead><tr><th>metric</th><th>value</th></tr></thead>"
    return f"<table>{head}<tbody>{rows}</tbody></table>"


def _drift_section() -> str:
    if DRIFT_HTML.exists():
        shutil.copy2(DRIFT_HTML, SITE / "drift_report.html")
        return (
            '<p>Full Evidently report: '
            '<a href="drift_report.html">drift_report.html</a> '
            "(comparison of the reference cohort with the current one).</p>"
            '<iframe src="drift_report.html" title="Drift report" '
            'style="width:100%;height:520px;border:1px solid #ddd;border-radius:8px"></iframe>'
        )
    return "<p><em>No drift_report.html — run: make gen-drift && make drift.</em></p>"


def _doc_section(name: str, title: str) -> str:
    path = DOCS / name
    if not path.exists():
        return f"<p><em>No {name}.</em></p>"
    return md_to_html(path.read_text(encoding="utf-8"))


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MLOps Churn Demo — report</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         max-width: 980px; margin: 2rem auto; padding: 0 1rem; line-height: 1.55; }}
  h1 {{ border-bottom: 3px solid #2563eb; padding-bottom: .3rem; }}
  h2 {{ margin-top: 2.2rem; border-bottom: 1px solid #ccc; padding-bottom: .2rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #ccc; padding: .4rem .6rem; text-align: left; }}
  th {{ background: rgba(37,99,235,.12); }}
  code {{ background: rgba(127,127,127,.18); padding: .1rem .3rem; border-radius: 4px; }}
  pre {{ background: rgba(127,127,127,.12); padding: .8rem; border-radius: 8px; overflow-x: auto; }}
  nav a {{ margin-right: 1rem; }}
  .badge {{ display:inline-block; background:#16a34a; color:#fff; padding:.1rem .5rem;
            border-radius:999px; font-size:.8rem; }}
</style>
</head>
<body>
<h1>MLOps Churn Demo <span class="badge">live report</span></h1>
<p>Static project report: latest model metrics, data drift report,
plus model/data cards and architecture. Generated by
<code>scripts/build_site.py</code> (target <code>make site</code>).</p>
<nav>
  <a href="#metrics">Metrics</a>
  <a href="#drift">Drift</a>
  <a href="#model">Model card</a>
  <a href="#data">Data card</a>
  <a href="#arch">Architecture</a>
</nav>

<h2 id="metrics">Latest model metrics</h2>
{metrics}

<h2 id="drift">Data drift report (Evidently)</h2>
{drift}

<h2 id="model">Model card</h2>
{model}

<h2 id="data">Data card</h2>
{data}

<h2 id="arch">Architecture</h2>
{arch}

<hr>
<p><small>Generated by build_site.py — MLOps Churn Demo.</small></p>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  mermaid.initialize({{ startOnLoad: true, theme: "default" }});
</script>
</body>
</html>
"""


def main() -> int:
    SITE.mkdir(parents=True, exist_ok=True)
    page = TEMPLATE.format(
        metrics=_metrics_table(),
        drift=_drift_section(),
        model=_doc_section("model_card.md", "Model card"),
        data=_doc_section("data_card.md", "Data card"),
        arch=_doc_section("architecture.md", "Architecture"),
    )
    out = SITE / "index.html"
    out.write_text(page, encoding="utf-8")
    # .nojekyll: Pages should not process the directory through Jekyll.
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    print(f"[site] Wrote {out} ({len(page)} bytes)")
    print(f"[site] Contents of site/: {sorted(p.name for p in SITE.iterdir())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
