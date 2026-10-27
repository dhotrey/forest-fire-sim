"""Port PowerPoint slides 1–6 into the existing S7 browser presentation."""

import argparse
import base64
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def run(*args, **kwargs):
    subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("powerpoint", type=Path)
    source = parser.parse_args().powerpoint.resolve()
    build = ROOT / ".build/imported-slides"
    assets = ROOT / "assets/intro"
    build.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)
    animations = []
    replacements = {}

    with ZipFile(source) as archive:
        presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
        dimensions = presentation.find("p:sldSz", NS).attrib
        width = 1920
        height = round(width * int(dimensions["cy"]) / int(dimensions["cx"]))
        rels = ET.fromstring(archive.read("ppt/_rels/presentation.xml.rels"))
        targets = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        slide_ids = list(presentation.find("p:sldIdLst", NS))[:6]
        if len(slide_ids) != 6:
            raise ValueError("The PowerPoint must contain at least six slides.")

        for number, slide_id in enumerate(slide_ids, 1):
            target = targets[slide_id.attrib[f"{{{NS['r']}}}id"]]
            slide_path = PurePosixPath("ppt") / target
            slide = ET.fromstring(archive.read(str(slide_path)))
            rel_path = slide_path.parent / "_rels" / (slide_path.name + ".rels")
            rels = ET.fromstring(archive.read(str(rel_path)))
            media = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
            changed = False
            for tree in slide.findall(".//p:spTree", NS):
                for picture in list(tree):
                    if picture.tag != f"{{{NS['p']}}}pic":
                        continue
                    blip = picture.find(".//a:blip", NS)
                    if blip is None:
                        continue
                    target = media.get(blip.attrib.get(f"{{{NS['r']}}}embed"), "")
                    if not target.lower().endswith(".gif"):
                        continue
                    # PowerPoint image relationships are relative to ppt/slides/.
                    media_name = os.path.normpath(str(slide_path.parent / target))
                    gif_path = assets / f"slide-{number}.gif"
                    gif_path.write_bytes(archive.read(media_name))
                    transform = picture.find("p:spPr/a:xfrm", NS)
                    offset = transform.find("a:off", NS).attrib
                    extent = transform.find("a:ext", NS).attrib
                    box = (
                        round(int(offset["x"]) * width / int(dimensions["cx"])),
                        round(int(offset["y"]) * height / int(dimensions["cy"])),
                        round(int(extent["cx"]) * width / int(dimensions["cx"])),
                        round(int(extent["cy"]) * height / int(dimensions["cy"])),
                    )
                    animations.append((number, gif_path, box))
                    tree.remove(picture)
                    changed = True
            if changed:
                replacements[str(slide_path)] = ET.tostring(
                    slide, encoding="utf-8", xml_declaration=True
                )

        rendering_copy = build / "intro-base.pptx"
        with ZipFile(rendering_copy, "w", ZIP_DEFLATED) as output:
            for entry in archive.infolist():
                output.writestr(
                    entry, replacements.get(entry.filename, archive.read(entry.filename))
                )

    # Render a copy; the user's editable PowerPoint is never modified.
    environment = os.environ | {"GSETTINGS_BACKEND": "memory", "SAL_USE_VCLPLUGIN": "svp"}
    run(
        "libreoffice",
        f"-env:UserInstallation={(build / 'lo-profile').as_uri()}",
        "--headless", "--convert-to", "pdf", "--outdir", str(build),
        str(rendering_copy), env=environment,
    )
    run(
        "pdftoppm", "-f", "1", "-l", "6", "-scale-to-x", str(width),
        "-scale-to-y", str(height), "-png", str(build / "intro-base.pdf"),
        str(assets / "slide"),
    )

    intro = {"slides": [], "resolution": [width, height], "background_color": "white"}
    for number in range(1, 7):
        media = f"assets/intro/slide-{number}.png"
        intro["slides"].append({
            "file": media, "rev_file": media,
            "type": "image", "loop": False, "auto_next": False,
        })
    (ROOT / "slides/Intro.json").write_text(json.dumps(intro, indent=2) + "\n")
    run(
        sys.executable, "-m", "manim_slides", "convert", "Intro", "S7AVX",
        "milestone2.html", "--one-file", "--offline", "-creveal_theme=white",
        "-cbackground_color=white", "-ccontrols=true", "-cmargin=0", "-chash=true",
        f"-cwidth={width}", f"-cheight={height}",
        "-ctitle=COSC3500 Milestone 2",
        env=os.environ | {"XDG_CACHE_HOME": str(ROOT / ".cache")},
    )
    # Keep the original GIF bytes and position them on the same slide canvas.
    # Both images scale together, including when the viewport has another aspect ratio.
    destination = ROOT / "milestone2.html"
    html = BeautifulSoup(destination.read_text(), "html.parser")
    sections = html.select(".slides > section")
    for number, gif_path, (x, y, w, h) in animations:
        section = sections[number - 1]
        background = section.attrs.pop("data-background-image")
        section["style"] = f"height:{height}px;padding:0"
        section["role"] = "img"
        section["aria-label"] = f"Slide {number}, with its animated forest-fire simulation"
        for src, left, top, image_width, image_height, rendering in (
            (background, 0, 0, width, height, "auto"),
            ("data:image/gif;base64," + base64.b64encode(gif_path.read_bytes()).decode(),
             x, y, w, h, "pixelated"),
        ):
            image = html.new_tag("img", src=src, alt="")
            image["aria-hidden"] = "true"
            image["style"] = (
                f"position:absolute;left:{left}px;top:{top}px;width:{image_width}px;"
                f"height:{image_height}px;margin:0;max-width:none;max-height:none;"
                f"border:0;box-shadow:none;image-rendering:{rendering}"
            )
            section.append(image)
    destination.write_text(str(html))
    print("Ready: milestone2.html — six imported slides followed by the four S7 stages.")


if __name__ == "__main__":
    main()
