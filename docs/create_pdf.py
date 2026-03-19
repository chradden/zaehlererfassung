#!/usr/bin/env python3
"""Konvertiert die Bedienungsanleitung von Markdown zu PDF."""

import os
import markdown
from weasyprint import HTML, CSS

MD_FILE = os.path.join(os.path.dirname(__file__), "Bedienungsanleitung_Zaehlererfassung.md")
PDF_FILE = os.path.join(os.path.dirname(__file__), "Bedienungsanleitung_Zaehlererfassung.pdf")

CSS_STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

@page {
    size: A4;
    margin: 2.5cm 2cm 2.5cm 2cm;
    @bottom-center {
        content: "Seite " counter(page) " von " counter(pages);
        font-size: 9pt;
        color: #888;
    }
    @top-right {
        content: "Zählererfassung – Bedienungsanleitung";
        font-size: 8pt;
        color: #aaa;
    }
}

body {
    font-family: 'Roboto', Arial, Helvetica, sans-serif;
    font-size: 10.5pt;
    line-height: 1.65;
    color: #222;
    background: white;
}

h1 {
    font-size: 22pt;
    font-weight: 700;
    color: #1a73e8;
    border-bottom: 3px solid #1a73e8;
    padding-bottom: 8px;
    margin-bottom: 18px;
    margin-top: 0;
}

h2 {
    font-size: 14pt;
    font-weight: 700;
    color: #1a73e8;
    border-bottom: 1px solid #cce0ff;
    padding-bottom: 4px;
    margin-top: 28px;
    margin-bottom: 12px;
    page-break-after: avoid;
}

h3 {
    font-size: 11pt;
    font-weight: 700;
    color: #333;
    margin-top: 18px;
    margin-bottom: 8px;
    page-break-after: avoid;
}

p {
    margin: 0 0 10px 0;
}

ul, ol {
    margin: 6px 0 10px 0;
    padding-left: 22px;
}

li {
    margin-bottom: 4px;
}

code {
    background: #f3f6fc;
    border: 1px solid #dde5f0;
    border-radius: 3px;
    padding: 1px 5px;
    font-family: 'Courier New', Courier, monospace;
    font-size: 9.5pt;
    color: #c7254e;
}

pre {
    background: #f3f6fc;
    border: 1px solid #dde5f0;
    border-left: 4px solid #1a73e8;
    border-radius: 4px;
    padding: 10px 14px;
    margin: 10px 0 14px 0;
    overflow-x: auto;
    page-break-inside: avoid;
}

pre code {
    background: transparent;
    border: none;
    padding: 0;
    color: #333;
    font-size: 9pt;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 16px 0;
    font-size: 10pt;
    page-break-inside: avoid;
}

th {
    background: #1a73e8;
    color: white;
    font-weight: 700;
    padding: 7px 10px;
    text-align: left;
    border: 1px solid #1a73e8;
}

td {
    padding: 6px 10px;
    border: 1px solid #d0daea;
}

tr:nth-child(even) td {
    background: #f3f7ff;
}

tr:nth-child(odd) td {
    background: white;
}

hr {
    border: none;
    border-top: 1px solid #dde5f0;
    margin: 20px 0;
}

strong {
    font-weight: 700;
    color: #111;
}

blockquote {
    border-left: 4px solid #1a73e8;
    margin: 10px 0;
    padding: 6px 14px;
    background: #f3f7ff;
    color: #444;
}

a {
    color: #1a73e8;
    text-decoration: none;
}
"""

def main():
    with open(MD_FILE, "r", encoding="utf-8") as f:
        md_content = f.read()

    html_body = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "toc"],
    )

    html_full = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>Zählererfassung – Bedienungsanleitung</title>
</head>
<body>
{html_body}
</body>
</html>"""

    HTML(string=html_full, base_url=os.path.dirname(MD_FILE)).write_pdf(
        PDF_FILE,
        stylesheets=[CSS(string=CSS_STYLE)],
    )

    print(f"PDF erstellt: {PDF_FILE}")


if __name__ == "__main__":
    main()
