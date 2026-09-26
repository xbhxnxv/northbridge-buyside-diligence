"""Repack an .xlsx or .docx so the same content always gives the same bytes.

Saving stamps the time into an Office file in three places, so a rerun with the same
numbers still changes the file:
  - the zip entry timestamps (LibreOffice and python-docx both write the current time);
  - docProps/core.xml: created, modified, lastModifiedBy, revision and lastPrinted;
  - xl/charts/*.xml: LibreOffice gives every chart axis a new random id on each save.

This script rewrites all three. Dates come from `document_date` in report_config.json.
Axis ids are renumbered in order of first appearance, keeping each axis paired with the
axis it crosses. Entries are written in a fixed order ([Content_Types].xml first, the
rest sorted) with the same compression settings every time. Cell values, formulas,
styles and text are not touched.

Usage: python tools/normalise_ooxml.py FILE [FILE ...]
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent

NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
}
DEFAULT_AUTHOR = "Northbridge pipeline"
AXIS_ID = re.compile(rb'(<c:(axId|crossAx) val=")(\d+)(")')


def document_date() -> dt.date:
    config = json.loads((ROOT / "report_config.json").read_text(encoding="utf-8"))
    return dt.date.fromisoformat(config["document_date"])


def _child(root: etree._Element, tag: str) -> etree._Element:
    prefix, local = tag.split(":")
    el = root.find(f"{prefix}:{local}", NS)
    if el is None:
        el = etree.SubElement(root, f"{{{NS[prefix]}}}{local}")
    return el


def core_xml(data: bytes, when: dt.date, docx: bool) -> bytes:
    root = etree.fromstring(data)
    stamp = f"{when.isoformat()}T00:00:00Z"
    for tag in ("dcterms:created", "dcterms:modified"):
        el = _child(root, tag)
        el.text = stamp
        el.set(f"{{{NS['xsi']}}}type", "dcterms:W3CDTF")
    author = _child(root, "dc:creator")
    if not (author.text or "").strip():
        author.text = DEFAULT_AUTHOR
    _child(root, "cp:lastModifiedBy").text = author.text
    _child(root, "cp:revision").text = "1"
    if docx:
        _child(root, "cp:lastPrinted").text = stamp
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def app_xml(data: bytes) -> bytes:
    root = etree.fromstring(data)
    total = root.find("ep:TotalTime", NS)
    if total is None or total.text == "0":
        return data
    total.text = "0"
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def chart_xml(data: bytes) -> bytes:
    ids: dict[bytes, bytes] = {}
    for m in AXIS_ID.finditer(data):
        if m.group(2) == b"axId" and m.group(3) not in ids:
            ids[m.group(3)] = str(100001 + len(ids)).encode()

    def swap(m: re.Match) -> bytes:
        if m.group(3) not in ids:
            raise ValueError(f"crossAx {m.group(3)!r} does not match any axId")
        return m.group(1) + ids[m.group(3)] + m.group(4)

    return AXIS_ID.sub(swap, data)


def normalise(path: Path, when: dt.date | None = None) -> bool:
    """Rewrite `path` in place. Returns True if the bytes changed."""
    path = Path(path)
    when = when or document_date()
    docx = path.suffix.lower() == ".docx"
    original = path.read_bytes()
    with zipfile.ZipFile(path) as z:
        entries = {i.filename: z.read(i.filename) for i in z.infolist() if not i.is_dir()}
    for name, data in entries.items():
        if name == "docProps/core.xml":
            entries[name] = core_xml(data, when, docx)
        elif name == "docProps/app.xml":
            entries[name] = app_xml(data)
        elif name.startswith("xl/charts/chart") and name.endswith(".xml"):
            entries[name] = chart_xml(data)
    order = sorted(entries, key=lambda n: (n != "[Content_Types].xml", n))
    tmp = path.with_name(path.name + ".tmp")
    with zipfile.ZipFile(tmp, "w") as z:
        for name in order:
            info = zipfile.ZipInfo(name, date_time=(when.year, when.month, when.day, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, entries[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    changed = tmp.read_bytes() != original
    tmp.replace(path)
    return changed


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    for f in argv:
        changed = normalise(Path(f))
        print(f"{f}: {'normalised' if changed else 'already normalised'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
