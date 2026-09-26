"""Fix the run-dependent metadata in a PDF so the same content always gives the same bytes.

LibreOffice writes the export time as /CreationDate, a random /ID and a /DocChecksum
that covers the export time into every PDF. This script removes /DocChecksum, sets
/CreationDate and /ModDate to `document_date` from report_config.json, sets the XMP
dates to the same value if the file has an XMP packet, and saves with an /ID derived
from the file's content (qpdf's deterministic ID). It then checks that the page count
and the extracted text are unchanged.

Usage: python tools/normalise_pdf.py FILE [FILE ...]
"""

from __future__ import annotations

import datetime as dt
import io
import sys
from pathlib import Path

import pikepdf
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalise_ooxml import document_date  # noqa: E402

XMP_DATES = ("xmp:CreateDate", "xmp:ModifyDate", "xmp:MetadataDate")


def _text(data: bytes) -> tuple[int, list[str]]:
    reader = PdfReader(io.BytesIO(data))
    return len(reader.pages), [p.extract_text() for p in reader.pages]


def normalise(path: Path, when: dt.date | None = None) -> bool:
    """Rewrite `path` in place. Returns True if the bytes changed."""
    path = Path(path)
    when = when or document_date()
    original = path.read_bytes()
    buf = io.BytesIO()
    with pikepdf.open(io.BytesIO(original)) as pdf:
        stamp = pikepdf.String(f"D:{when:%Y%m%d}000000Z")
        pdf.docinfo["/CreationDate"] = stamp
        pdf.docinfo["/ModDate"] = stamp
        if "/Metadata" in pdf.Root:
            with pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=False) as meta:
                for key in XMP_DATES:
                    if key in meta:
                        meta[key] = f"{when.isoformat()}T00:00:00Z"
        # /ID: qpdf would keep the old random first element. /DocChecksum: a LibreOffice-only
        # trailer key computed over the export time; no PDF reader uses it.
        for key in ("/ID", "/DocChecksum"):
            if key in pdf.trailer:
                del pdf.trailer[key]
        pdf.save(buf, deterministic_id=True)
    data = buf.getvalue()
    if _text(data) != _text(original):
        raise RuntimeError(f"{path}: page count or text changed while normalising metadata")
    path.write_bytes(data)
    return data != original


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
