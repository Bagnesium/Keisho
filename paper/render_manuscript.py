#!/usr/bin/env python3
"""Render the canonical manuscript Markdown as plain text and print-ready HTML."""

from __future__ import annotations

import html
import re
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "MANUSCRIPT_FINAL_PILOT.md"


def is_table_row(line: str) -> bool:
    return line.strip().startswith("|") and line.strip().endswith("|")


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def inline_html(value: str) -> str:
    value = html.escape(value, quote=False)
    code: list[str] = []

    def hold(match: re.Match[str]) -> str:
        code.append(f"<code>{match.group(1)}</code>")
        return f"\x00CODE{len(code) - 1}\x00"

    value = re.sub(r"`([^`]+)`", hold, value)
    value = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", value)
    for index, fragment in enumerate(code):
        value = value.replace(f"\x00CODE{index}\x00", fragment)
    return value


def inline_text(value: str) -> str:
    value = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = value.replace("**", "").replace("*", "")
    return value


def render_html(markdown: str) -> str:
    lines = markdown.splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        if line.startswith("```"):
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index])
                index += 1
            blocks.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
            index += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{inline_html(heading.group(2))}</h{level}>")
            index += 1
            continue

        if is_table_row(line):
            rows: list[list[str]] = []
            while index < len(lines) and is_table_row(lines[index]):
                rows.append(table_cells(lines[index]))
                index += 1
            if len(rows) > 1 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in rows[1]):
                rows.pop(1)
            if rows:
                head = "".join(f"<th>{inline_html(cell)}</th>" for cell in rows[0])
                body = "".join(
                    "<tr>" + "".join(f"<td>{inline_html(cell)}</td>" for cell in row) + "</tr>"
                    for row in rows[1:]
                )
                blocks.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
            continue

        if re.match(r"^\s*[-*]\s+", line):
            items: list[str] = []
            while index < len(lines) and re.match(r"^\s*[-*]\s+", lines[index]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[index]))
                index += 1
            blocks.append("<ul>" + "".join(f"<li>{inline_html(item)}</li>" for item in items) + "</ul>")
            continue

        if re.match(r"^\s*\d+\.\s+", line):
            items = []
            while index < len(lines) and re.match(r"^\s*\d+\.\s+", lines[index]):
                items.append(re.sub(r"^\s*\d+\.\s+", "", lines[index]))
                index += 1
            blocks.append("<ol>" + "".join(f"<li>{inline_html(item)}</li>" for item in items) + "</ol>")
            continue

        paragraph = [line.strip()]
        index += 1
        while index < len(lines) and lines[index].strip() and not (
            lines[index].startswith("#")
            or lines[index].startswith("```")
            or is_table_row(lines[index])
            or re.match(r"^\s*[-*]\s+", lines[index])
            or re.match(r"^\s*\d+\.\s+", lines[index])
        ):
            paragraph.append(lines[index].strip())
            index += 1
        content = inline_html(" ".join(paragraph))
        ref_class = " class=\"reference\"" if re.match(r"^\[\d+\]", paragraph[0]) else ""
        blocks.append(f"<p{ref_class}>{content}</p>")

    body = "\n".join(blocks)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Exploratory single-task study of coding-agent handoff conditions on SWE-bench Verified.">
<title>Typed Evidence Handoffs in a Coding-Agent Takeover</title>
<style>
:root {{ color-scheme: light; }}
* {{ box-sizing: border-box; }}
body {{ max-width: 8.25in; margin: 2rem auto; padding: 0 1rem; color: #171717; background: #fff; font-family: Georgia, "Times New Roman", serif; font-size: 11pt; line-height: 1.42; }}
h1, h2, h3, h4, h5, h6 {{ color: #111; line-height: 1.18; break-after: avoid; }}
h1 {{ margin: 0 0 1.25rem; text-align: center; font-size: 19pt; }}
h1 + p {{ text-align: center; margin: .25rem 0; }}
h1 + p + p {{ text-align: center; font-size: 10pt; margin: .2rem 0 1.2rem; }}
h2 {{ margin: 1.45rem 0 .5rem; font-size: 14pt; }}
h3 {{ margin: 1rem 0 .35rem; font-size: 12pt; }}
p {{ margin: .42rem 0; text-align: justify; orphans: 2; widows: 2; }}
p.reference {{ padding-left: 1.2rem; text-indent: -1.2rem; overflow-wrap: anywhere; }}
ul, ol {{ margin: .35rem 0 .7rem; padding-left: 1.5rem; }}
li {{ margin: .2rem 0; }}
table {{ width: 100%; margin: .7rem 0 1rem; border-collapse: collapse; font-family: Arial, sans-serif; font-size: 8.5pt; line-height: 1.25; break-inside: avoid; }}
th, td {{ border: 1px solid #777; padding: .32rem .38rem; text-align: left; vertical-align: top; }}
th {{ background: #f0f0f0; font-weight: 700; }}
tbody tr:nth-child(even) {{ background: #fafafa; }}
code {{ font-family: "SFMono-Regular", Consolas, monospace; font-size: .88em; overflow-wrap: anywhere; }}
a {{ color: #174a73; text-decoration: none; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere; padding: .7rem; background: #f5f5f5; }}
@page {{ size: Letter; margin: .78in .82in .78in; }}
@media print {{
  body {{ max-width: none; margin: 0; padding: 0; font-size: 10.5pt; line-height: 1.34; }}
  h1 {{ font-size: 18pt; }}
  h2 {{ margin-top: 1.2rem; }}
  a {{ color: inherit; }}
  table {{ font-size: 8pt; }}
  th {{ background: #eee !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  tbody tr:nth-child(even) {{ background: #fafafa !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
}}
</style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def render_text(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            title = inline_text(heading.group(2))
            output.extend([title, "=" * min(len(title), 88) if len(heading.group(1)) == 1 else "-" * min(len(title), 88), ""])
            index += 1
            continue

        if line.startswith("```"):
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                output.append("    " + lines[index])
                index += 1
            index += 1
            output.append("")
            continue

        if is_table_row(line):
            while index < len(lines) and is_table_row(lines[index]):
                cells = table_cells(lines[index])
                if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    output.append(" | ".join(inline_text(cell) for cell in cells))
                index += 1
            output.append("")
            continue

        bullet = re.match(r"^\s*[-*]\s+(.*)$", line)
        ordered = re.match(r"^\s*(\d+)\.\s+(.*)$", line)
        if bullet or ordered:
            while index < len(lines):
                bullet = re.match(r"^\s*[-*]\s+(.*)$", lines[index])
                ordered = re.match(r"^\s*(\d+)\.\s+(.*)$", lines[index])
                if not bullet and not ordered:
                    break
                item = inline_text((bullet or ordered).group(1) if bullet else ordered.group(2))
                prefix = "- " if bullet else f"{ordered.group(1)}. "
                output.extend(textwrap.wrap(prefix + item, width=96, subsequent_indent="  ", break_long_words=False, break_on_hyphens=False))
                index += 1
            output.append("")
            continue

        paragraph = [line.strip()]
        index += 1
        while index < len(lines) and lines[index].strip() and not (
            lines[index].startswith("#")
            or lines[index].startswith("```")
            or is_table_row(lines[index])
            or re.match(r"^\s*[-*]\s+", lines[index])
            or re.match(r"^\s*\d+\.\s+", lines[index])
        ):
            paragraph.append(lines[index].strip())
            index += 1
        plain = inline_text(" ".join(paragraph))
        output.extend(textwrap.wrap(plain, width=96, break_long_words=False, break_on_hyphens=False) or [""])
        output.append("")

    return "\n".join(output).rstrip() + "\n"


def main() -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    (ROOT / "MANUSCRIPT_FINAL_PILOT.txt").write_text(render_text(markdown), encoding="utf-8")
    (ROOT / "MANUSCRIPT_FINAL_PILOT.html").write_text(render_html(markdown), encoding="utf-8")


if __name__ == "__main__":
    main()
