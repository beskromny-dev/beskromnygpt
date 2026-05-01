"""Render the digest markdown into a styled PDF with clickable links."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import markdown as md_lib
from weasyprint import CSS, HTML

logger = logging.getLogger(__name__)


PDF_CSS = """
@page {
    size: A4;
    margin: 2cm 2cm 2.2cm 2cm;
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-family: 'Helvetica', 'Arial', sans-serif;
        font-size: 9pt;
        color: #999;
    }
}

body {
    font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif;
    font-size: 11pt;
    line-height: 1.55;
    color: #1a1a1a;
}

.masthead {
    border-bottom: 1px solid #ddd;
    padding-bottom: 14px;
    margin-bottom: 24px;
}
.masthead .brand {
    font-size: 20pt;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin: 0;
}
.masthead .date {
    font-size: 12pt;
    color: #666;
    margin-top: 4px;
}

h1, h2, h3, h4 {
    font-weight: 700;
    color: #111;
    page-break-after: avoid;
    letter-spacing: -0.01em;
}

h2 {
    font-size: 14pt;
    margin-top: 22px;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1px solid #eee;
    padding-bottom: 4px;
}

h3 {
    font-size: 12pt;
    margin-top: 16px;
    margin-bottom: 4px;
}

h4 {
    font-size: 11pt;
    margin-top: 12px;
    margin-bottom: 3px;
}

p {
    margin: 6px 0 10px;
    text-align: left;
}

a {
    color: #1a56db;
    text-decoration: none;
    word-break: break-word;
}

a:hover { text-decoration: underline; }

strong { font-weight: 600; color: #000; }

hr {
    border: none;
    border-top: 1px solid #eee;
    margin: 18px 0;
}

blockquote {
    border-left: 3px solid #ddd;
    padding-left: 12px;
    color: #555;
    margin: 10px 0;
    font-style: italic;
}

ol, ul { padding-left: 22px; margin: 6px 0 10px; }
li { margin-bottom: 4px; }

.source-link {
    display: block;
    margin-top: 2px;
    font-size: 10pt;
}
.source-link::before {
    content: "→ ";
    color: #999;
}

.footer {
    margin-top: 28px;
    padding-top: 12px;
    border-top: 1px solid #eee;
    font-size: 9pt;
    color: #888;
    text-align: center;
}
"""


def _preprocess_markdown(text: str) -> str:
    """Turn lines that are just a single link into arrow-prefixed source-link class."""
    lines = text.split("\n")
    out = []
    link_only = re.compile(r"^\s*\[([^\]]+)\]\(([^)]+)\)\s*$")
    for line in lines:
        m = link_only.match(line)
        if m:
            out.append(f'<p class="source-link"><a href="{m.group(2)}">{m.group(1)}</a></p>')
        else:
            out.append(line)
    return "\n".join(out)


def render_digest_pdf(markdown_text: str, date_label: str, output_path: Path) -> Path:
    """Render the digest markdown as a styled PDF. Returns the output path."""
    processed = _preprocess_markdown(markdown_text)
    body_html = md_lib.markdown(
        processed,
        extensions=["extra", "sane_lists", "smarty"],
    )

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8" />
    <title>#beskromny_digest — {date_label}</title>
</head>
<body>
    <header class="masthead">
        <p class="brand">#beskromny_digest</p>
        <p class="date">{date_label}</p>
    </header>
    <main>
        {body_html}
    </main>
    <div class="footer">
        Сгенерировано БескромныйGPT · t.me/dbeskromny
    </div>
</body>
</html>
"""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html).write_pdf(str(output_path), stylesheets=[CSS(string=PDF_CSS)])
    logger.info("PDF generated: %s", output_path)
    return output_path
