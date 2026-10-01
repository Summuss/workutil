"""Red boxes in the exported workbook, as native Excel rectangles.

A red box (CONTEXT.md) has to arrive in Excel as a shape that can still be
clicked, dragged and deleted, the way the hand-made evidence it sits beside
was marked up — not as pixels burnt into the screenshot (ADR-0014).

openpyxl 3.1.5 cannot write shapes: `SpreadsheetDrawing._write` walks only
`charts + images`, and its `GroupShape` holds a single `pic`. So the workbook
is saved as usual and then its `xl/drawings/drawingN.xml` are rewritten: each
screenshot that carries boxes is moved into a group together with one
rectangle per box. The group's own coordinates are the screenshot's, so a box
lands where it was drawn without going through any row height or column width
— the units that shift with Windows display scaling (design.md §6 F5).
"""

import io
import posixpath
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from xml.etree import ElementTree as ET

from app.modules.evidence.models import Box

XDR_NS = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
DRAWINGML_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DRAWING_REL_TYPE = f"{OFFICE_REL_NS}/drawing"

# The prefixes Excel itself writes. Any would be valid XML; these keep the
# rewritten part looking like the one openpyxl wrote.
ET.register_namespace("xdr", XDR_NS)
ET.register_namespace("a", DRAWINGML_NS)
ET.register_namespace("r", OFFICE_REL_NS)


def _xdr(tag: str) -> str:
    return f"{{{XDR_NS}}}{tag}"


def _a(tag: str) -> str:
    return f"{{{DRAWINGML_NS}}}{tag}"


@dataclass(frozen=True)
class ImageBoxes:
    """One screenshot on a sheet, as far as its boxes are concerned.

    The size is the stored file's, the unit the boxes are in. The drawing only
    knows the size the picture is shown at, and the two axes were rounded
    separately on the way there, so each needs its own ratio — one shared
    ratio puts a box at the bottom of a long screenshot visibly off.
    """

    src_width: int
    src_height: int
    boxes: Sequence[Box] = ()


@dataclass(frozen=True)
class BoxStyle:
    """How a box is drawn in Excel; the values live in `LayoutSettings`."""

    color: str
    line_emu: int


def inject_boxes(
    workbook_bytes: bytes,
    sheets: Sequence[Sequence[ImageBoxes]],
    style: BoxStyle,
) -> bytes:
    """Add the red boxes to a saved workbook.

    `sheets` lists, in workbook order, each sheet's screenshots in the order
    they were added to it. A workbook without a single box comes back as the
    very same bytes, and a sheet without one keeps its drawing untouched.
    """
    if not any(img.boxes for images in sheets for img in images):
        return workbook_bytes

    package = zipfile.ZipFile(io.BytesIO(workbook_bytes))
    sheet_paths = _sheet_paths(package)
    if len(sheet_paths) != len(sheets):
        raise ValueError(
            f"工作簿有 {len(sheet_paths)} 个 sheet,却给了 {len(sheets)} 份图片清单"
        )

    rewritten: dict[str, bytes] = {}
    for sheet_path, images in zip(sheet_paths, sheets, strict=True):
        if not any(img.boxes for img in images):
            continue
        drawing_path = _drawing_of(package, sheet_path)
        if drawing_path is None:
            raise ValueError(f"{sheet_path} 上有图片却找不到它的 drawing")
        rewritten[drawing_path] = _with_boxes(
            package.read(drawing_path), images, style, sheet_path
        )

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as rebuilt:
        for item in package.infolist():
            rebuilt.writestr(
                item, rewritten.get(item.filename) or package.read(item.filename)
            )
    return out.getvalue()


def _resolve(base_dir: str, target: str) -> str:
    """A relationship target as a path inside the package."""
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(base_dir, target))


def _sheet_paths(package: zipfile.ZipFile) -> list[str]:
    """Every worksheet's part, in the order the workbook lists its sheets."""
    workbook = ET.fromstring(package.read("xl/workbook.xml"))
    rels = ET.fromstring(package.read("xl/_rels/workbook.xml.rels"))
    targets = {
        rel.get("Id"): rel.get("Target", "")
        for rel in rels.iter(f"{{{PACKAGE_REL_NS}}}Relationship")
    }
    return [
        _resolve("xl", targets[sheet.get(f"{{{OFFICE_REL_NS}}}id")])
        for sheet in workbook.iter(f"{{{SPREADSHEET_NS}}}sheet")
    ]


def _drawing_of(package: zipfile.ZipFile, sheet_path: str) -> str | None:
    """The drawing part a sheet points at, read from its relationships.

    Never worked out from the sheet's position: a sheet without pictures has
    no drawing, so the n-th sheet's drawing is not `drawingN.xml` as soon as
    an earlier sheet has none.
    """
    sheet_dir, sheet_file = posixpath.split(sheet_path)
    rels_path = posixpath.join(sheet_dir, "_rels", f"{sheet_file}.rels")
    if rels_path not in package.namelist():
        return None
    rels = ET.fromstring(package.read(rels_path))
    for rel in rels.iter(f"{{{PACKAGE_REL_NS}}}Relationship"):
        if rel.get("Type") == DRAWING_REL_TYPE:
            return _resolve(sheet_dir, rel.get("Target", ""))
    return None


def _with_boxes(
    drawing_xml: bytes,
    images: Sequence[ImageBoxes],
    style: BoxStyle,
    sheet_path: str,
) -> bytes:
    """The drawing with each boxed screenshot grouped with its rectangles."""
    root = ET.fromstring(drawing_xml)
    anchors = [anchor for anchor in root if anchor.find(_xdr("pic")) is not None]
    if len(anchors) != len(images):
        # Pairing them up regardless would put boxes on the wrong screenshot.
        raise ValueError(
            f"{sheet_path} 的 drawing 里有 {len(anchors)} 张图,"
            f"却给了 {len(images)} 张图的红框"
        )

    # Shape ids only have to be unique within the drawing.
    ids = (int(el.get("id", "0")) for el in root.iter(_xdr("cNvPr")))
    next_id = max(ids, default=0) + 1

    for anchor, image in zip(anchors, images, strict=True):
        if not image.boxes:
            continue
        ext = anchor.find(_xdr("ext"))
        pic = anchor.find(_xdr("pic"))
        assert ext is not None and pic is not None
        size = (int(ext.get("cx", "0")), int(ext.get("cy", "0")))
        kx = size[0] / image.src_width
        ky = size[1] / image.src_height

        group = ET.Element(_xdr("grpSp"))
        _name(group, "nvGrpSpPr", "cNvGrpSpPr", next_id, "Group")
        next_id += 1
        # off/ext equal to chOff/chExt: a child's coordinates are the
        # screenshot's own, whatever cell the group is anchored to.
        _xfrm(ET.SubElement(group, _xdr("grpSpPr")), (0, 0), size, children=True)

        position = list(anchor).index(pic)
        anchor.remove(pic)
        # Inside a group a picture needs its own place in the group's space;
        # anchored directly it took that from the anchor.
        pic_props = pic.find(_xdr("spPr"))
        assert pic_props is not None
        pic_props.insert(0, _xfrm(None, (0, 0), size))
        group.append(pic)

        for box in image.boxes:
            group.append(
                _rectangle(
                    next_id,
                    (round(box["x"] * kx), round(box["y"] * ky)),
                    (round(box["w"] * kx), round(box["h"] * ky)),
                    style,
                )
            )
            next_id += 1
        anchor.insert(position, group)

    # `encoding="unicode"` and no declaration of ElementTree's own: the one
    # written here is the one openpyxl and Excel write, `standalone` included.
    body = ET.tostring(root, encoding="unicode")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + body).encode()


def _name(parent: ET.Element, props: str, kind: str, shape_id: int, label: str) -> None:
    """The non-visual properties every shape opens with: its id and name."""
    non_visual = ET.SubElement(parent, _xdr(props))
    ET.SubElement(
        non_visual, _xdr("cNvPr"), {"id": str(shape_id), "name": f"{label} {shape_id}"}
    )
    ET.SubElement(non_visual, _xdr(kind))


def _xfrm(
    parent: ET.Element | None,
    off: tuple[int, int],
    ext: tuple[int, int],
    *,
    children: bool = False,
) -> ET.Element:
    """An `a:xfrm` at `off` sized `ext`; `children` maps a group's space 1:1."""
    xfrm = (
        ET.Element(_a("xfrm")) if parent is None else ET.SubElement(parent, _a("xfrm"))
    )
    ET.SubElement(xfrm, _a("off"), {"x": str(off[0]), "y": str(off[1])})
    ET.SubElement(xfrm, _a("ext"), {"cx": str(ext[0]), "cy": str(ext[1])})
    if children:
        ET.SubElement(xfrm, _a("chOff"), {"x": str(off[0]), "y": str(off[1])})
        ET.SubElement(xfrm, _a("chExt"), {"cx": str(ext[0]), "cy": str(ext[1])})
    return xfrm


def _rectangle(
    shape_id: int, off: tuple[int, int], ext: tuple[int, int], style: BoxStyle
) -> ET.Element:
    """One red box: an unfilled rectangle with a solid outline."""
    shape = ET.Element(_xdr("sp"), {"macro": "", "textlink": ""})
    _name(shape, "nvSpPr", "cNvSpPr", shape_id, "Rectangle")
    props = ET.SubElement(shape, _xdr("spPr"))
    _xfrm(props, off, ext)
    geometry = ET.SubElement(props, _a("prstGeom"), {"prst": "rect"})
    ET.SubElement(geometry, _a("avLst"))
    ET.SubElement(props, _a("noFill"))
    line = ET.SubElement(props, _a("ln"), {"w": str(style.line_emu)})
    fill = ET.SubElement(line, _a("solidFill"))
    ET.SubElement(fill, _a("srgbClr"), {"val": style.color})
    return shape
