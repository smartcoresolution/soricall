#!/usr/bin/env python3
"""Convert the current SoriCall Markdown specification to a styled DOCX."""

from __future__ import annotations

import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "technical_spec_current.md"
OUTPUT = ROOT / "docs" / "technical_spec_current.docx"


def run(text: str, *, bold: bool = False, code: bool = False) -> str:
    properties = []
    if bold:
        properties.append("<w:b/>")
    if code:
        properties.extend(
            [
                '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="D2Coding"/>',
                '<w:sz w:val="18"/>',
                '<w:color w:val="333333"/>',
            ]
        )
    prop_xml = f"<w:rPr>{''.join(properties)}</w:rPr>" if properties else ""
    preserve = ' xml:space="preserve"' if text[:1].isspace() or text[-1:].isspace() else ""
    return f"<w:r>{prop_xml}<w:t{preserve}>{escape(text)}</w:t></w:r>"


def inline_runs(text: str) -> str:
    parts = re.split(r"(`[^`]+`|\*\*[^*]+\*\*)", text)
    output = []
    for part in parts:
        if part.startswith("`") and part.endswith("`"):
            output.append(run(part[1:-1], code=True))
        elif part.startswith("**") and part.endswith("**"):
            output.append(run(part[2:-2], bold=True))
        elif part:
            output.append(run(part))
    return "".join(output)


def paragraph(
    text: str = "",
    *,
    style: str | None = None,
    before: int = 0,
    after: int = 120,
    indent: int = 0,
    shade: str | None = None,
    code: bool = False,
) -> str:
    p_props = []
    if style:
        p_props.append(f'<w:pStyle w:val="{style}"/>')
    p_props.append(f'<w:spacing w:before="{before}" w:after="{after}" w:line="300" w:lineRule="auto"/>')
    if indent:
        p_props.append(f'<w:ind w:left="{indent}"/>')
    if shade:
        p_props.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>')
    contents = run(text, code=True) if code else inline_runs(text)
    return f"<w:p><w:pPr>{''.join(p_props)}</w:pPr>{contents}</w:p>"


def list_paragraph(text: str, *, level: int = 0, ordered: bool = False) -> str:
    num_id = 2 if ordered else 1
    return (
        "<w:p><w:pPr>"
        f'<w:numPr><w:ilvl w:val="{min(level, 2)}"/><w:numId w:val="{num_id}"/></w:numPr>'
        f'<w:ind w:left="{720 + level * 360}" w:hanging="360"/>'
        '<w:spacing w:after="60" w:line="300" w:lineRule="auto"/>'
        f"</w:pPr>{inline_runs(text)}</w:p>"
    )


def table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    column_count = max(len(row) for row in rows)
    width = 9000 // column_count
    grid = "".join(f'<w:gridCol w:w="{width}"/>' for _ in range(column_count))
    row_xml = []
    for row_index, row in enumerate(rows):
        cells = []
        for value in row + [""] * (column_count - len(row)):
            fill = '<w:shd w:val="clear" w:color="auto" w:fill="DDEFEA"/>' if row_index == 0 else ""
            bold = row_index == 0
            cells.append(
                "<w:tc>"
                f'<w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{fill}'
                '<w:tcMar><w:top w:w="90" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
                '<w:bottom w:w="90" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tcMar></w:tcPr>'
                f'<w:p><w:pPr><w:spacing w:after="0"/></w:pPr>{run(value, bold=bold)}</w:p>'
                "</w:tc>"
            )
        row_xml.append(f"<w:tr>{''.join(cells)}</w:tr>")
    borders = (
        '<w:tblBorders><w:top w:val="single" w:sz="4" w:color="B8C8C4"/>'
        '<w:left w:val="single" w:sz="4" w:color="B8C8C4"/>'
        '<w:bottom w:val="single" w:sz="4" w:color="B8C8C4"/>'
        '<w:right w:val="single" w:sz="4" w:color="B8C8C4"/>'
        '<w:insideH w:val="single" w:sz="4" w:color="B8C8C4"/>'
        '<w:insideV w:val="single" w:sz="4" w:color="B8C8C4"/></w:tblBorders>'
    )
    return (
        '<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/>'
        f'<w:tblLayout w:type="fixed"/>{borders}</w:tblPr><w:tblGrid>{grid}</w:tblGrid>'
        f"{''.join(row_xml)}</w:tbl>"
        '<w:p><w:pPr><w:spacing w:after="80"/></w:pPr></w:p>'
    )


def markdown_to_body(markdown: str) -> str:
    lines = markdown.splitlines()
    blocks: list[str] = []
    index = 0
    in_code = False
    code_lines: list[str] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_lines:
            blocks.append(paragraph(" ".join(line.strip() for line in paragraph_lines)))
            paragraph_lines.clear()

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            if in_code:
                for code_line in code_lines or [""]:
                    blocks.append(paragraph(code_line, after=0, indent=180, shade="F3F5F4", code=True))
                blocks.append(paragraph("", after=100, shade="F3F5F4"))
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            index += 1
            continue

        if in_code:
            code_lines.append(line)
            index += 1
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            rows = [
                [cell.strip() for cell in row.strip("|").split("|")]
                for row in table_lines
                if not re.fullmatch(r"\|?[\s:|-]+\|?", row)
                and not all(re.fullmatch(r":?-+:?", cell.strip()) for cell in row.strip("|").split("|"))
            ]
            blocks.append(table(rows))
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            level = min(len(heading.group(1)), 3)
            blocks.append(paragraph(heading.group(2), style=f"Heading{level}", before=180, after=100))
            index += 1
            continue

        if stripped == "---":
            flush_paragraph()
            blocks.append(
                '<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" w:color="7CA99D"/>'
                '</w:pBdr><w:spacing w:after="120"/></w:pPr></w:p>'
            )
            index += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            blocks.append(paragraph(stripped.lstrip("> ").strip(), indent=360, shade="EEF6F4"))
            index += 1
            continue

        bullet = re.match(r"^(\s*)[-*]\s+(.+)$", line)
        ordered = re.match(r"^(\s*)\d+\.\s+(.+)$", line)
        if bullet or ordered:
            flush_paragraph()
            match = bullet or ordered
            assert match is not None
            blocks.append(
                list_paragraph(
                    match.group(2),
                    level=len(match.group(1)) // 2,
                    ordered=ordered is not None,
                )
            )
            index += 1
            continue

        if not stripped:
            flush_paragraph()
        else:
            paragraph_lines.append(line)
        index += 1

    flush_paragraph()
    return "".join(blocks)


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

DOCUMENT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="맑은 고딕"/>
<w:sz w:val="21"/><w:lang w:val="ko-KR" w:eastAsia="ko-KR"/></w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>
<w:pPr><w:keepNext/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="125E52"/><w:sz w:val="34"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>
<w:pPr><w:keepNext/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:color w:val="1B7465"/><w:sz w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/>
<w:pPr><w:keepNext/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:color w:val="274E47"/><w:sz w:val="24"/></w:rPr></w:style>
</w:styles>"""

NUMBERING = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="multilevel"/>
<w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:rPr><w:rFonts w:ascii="Arial"/></w:rPr></w:lvl>
<w:lvl w:ilvl="1"><w:numFmt w:val="bullet"/><w:lvlText w:val="◦"/></w:lvl>
<w:lvl w:ilvl="2"><w:numFmt w:val="bullet"/><w:lvlText w:val="▪"/></w:lvl></w:abstractNum>
<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="multilevel"/>
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1.%2."/></w:lvl>
<w:lvl w:ilvl="2"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1.%2.%3."/></w:lvl></w:abstractNum>
<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
<w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num>
</w:numbering>"""


def main() -> None:
    body = markdown_to_body(SOURCE.read_text(encoding="utf-8"))
    section = (
        "<w:sectPr>"
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" '
        'w:header="708" w:footer="708" w:gutter="0"/>'
        "</w:sectPr>"
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}{section}</w:body></w:document>"
    )
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"
xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>SoriCall 현행 구현 기술 사양서</dc:title><dc:creator>SoriCall</dc:creator>
<dc:subject>Current implementation technical specification</dc:subject>
<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>"""
    app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<Application>SoriCall DOCX Exporter</Application></Properties>"""

    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", ROOT_RELS)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", STYLES)
        archive.writestr("word/numbering.xml", NUMBERING)
        archive.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS)
        archive.writestr("docProps/core.xml", core)
        archive.writestr("docProps/app.xml", app)

    print(OUTPUT)


if __name__ == "__main__":
    main()
