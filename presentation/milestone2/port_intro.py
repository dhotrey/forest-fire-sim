"""Build the final browser deck from the original intro and Manim scenes."""

import argparse
import base64
import json
import os
import re
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
                    if number in (3, 4) and target.lower().endswith(".png"):
                        filename = "node-info.png" if number == 3 else "build-info.png"
                        media_name = os.path.normpath(str(slide_path.parent / target))
                        (assets / filename).write_bytes(archive.read(media_name))
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

    deck = {"slides": [], "resolution": [width, height], "background_color": "white"}
    groups = []
    script = (ROOT / "script-milestone-2.md").read_text()
    spoken = {}
    for match in re.finditer(r"^## S(\d+)[^\n]*\n(.*?)(?=^## |\Z)", script, re.M | re.S):
        body = re.sub(r"```.*?```", "", match[2], flags=re.S)
        body = re.sub(r"(?m)^\*.*?\*(?=\n|$)", "", body, flags=re.S)
        spoken[int(match[1])] = body.replace("---", "").strip()
    sources = {
        2: "https://doi.org/10.1103/PhysRevLett.69.1629",
        6: "https://clang.llvm.org/doxygen/avxintrin_8h.html",
        7: "https://clang.llvm.org/doxygen/avx2intrin_8h.html",
        8: "https://github.com/wjakob/pcg32; https://clang.llvm.org/doxygen/avx2intrin_8h.html",
        9: "https://clang.llvm.org/doxygen/avx2intrin_8h.html",
        10: "https://clang.llvm.org/doxygen/avx2intrin_8h.html",
        11: "data/v1.0/benchmarking/benchmarks-o3.csv; data/v1.1/benchmarking/benchmarks-o3.csv",
        12: "main.cpp at v1.3; https://www.openmp.org/spec-html/5.2/openmpse62.html",
        13: "data/v1.3/{4,5,6,7,8}-threads/benchmarking/benchmarks-o3.csv; https://hpc.llnl.gov/documentation/tutorials/introduction-parallel-computing-tutorial",
        14: "data/v1.0, data/v1.1 and data/v1.3/8-threads benchmark CSVs; same CPU model, different physical nodes",
        15: "main.cpp; pcg32_8.h; presenter-reported rule-level checks",
        16: "Presenter-provided disclosure; slides/milestone1.pdf, page 23",
        17: "See bibliography; https://docs.manim.community/en/v0.19.0/",
    }
    sequence = [
        (1, 1), (2, 2), (3, "S3Methodology"), (4, 5), (5, 6),
        (6, "S7AVX"), (7, "S8Neighbours"), (7, "S9FireMask"),
        (8, "S10RNGChecks"), (8, "S11PackMasks"), (9, "S9RuleMasks"),
        (10, "S10Blending"), (11, "S11AVXResults"), (12, "S12OpenMP"),
        (13, "S13Scaling"), (14, "S14Combined"), (15, "S15Reflection"),
        (16, "S16AIDisclosure"), (17, "S17Bibliography"),
    ]
    static_images = {
        "S9RuleMasks": "assets/rule-masks.png",
        "S10Blending": "assets/blending.png",
    }
    for logical, scene in sequence:
        if isinstance(scene, int):
            media = f"assets/intro/slide-{scene}.png"
            slides = [{"file": media, "rev_file": media, "type": "image",
                       "loop": False, "auto_next": False}]
        else:
            slides = json.loads((ROOT / f"slides/{scene}.json").read_text())["slides"]
            if scene in static_images:
                # Export the completed static layout as an image, without a video player.
                media = static_images[scene]
                run("ffmpeg", "-v", "error", "-y", "-sseof", "-0.1", "-i",
                    slides[0]["file"], "-frames:v", "1", str(ROOT / media))
                slides = [{"file": media, "rev_file": media, "type": "image",
                           "loop": False, "auto_next": False}]
        for slide in slides:
            slide["auto_next"] = False
            slide["playback_rate"] = 1.0
            slide["reversed_playback_rate"] = slide["playback_rate"]
            slide["notes"] = spoken.get(logical, "") + "\n\nSources: " + sources.get(logical, "See bibliography.")
            deck["slides"].append(slide)
            groups.append(logical)
    (ROOT / "slides/Milestone2.json").write_text(json.dumps(deck, indent=2) + "\n")
    run(
        sys.executable, "-m", "manim_slides", "convert", "Milestone2",
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
    seen = {}
    for section, logical in zip(sections, groups, strict=True):
        seen[logical] = seen.get(logical, 0) + 1
        step = seen[logical]
        section["id"] = f"s{logical}" if step == 1 else f"s{logical}-step-{step}"
        section["data-script-slide"] = str(logical)
        section["aria-label"] = f"Script slide {logical}, stage {step}"
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
    counter = html.new_tag("script")
    counter.string = """
    Reveal.configure({
      slideNumber: slide => [Number((slide && slide.dataset.scriptSlide) || 1), ' / ', 17]
    });
    """
    html.body.append(counter)
    # Reveal splits a background-video string on commas. A data URI contains
    # a comma, and the converter's lazy-video repair can run before its sources
    # exist. Blob URLs keep each embedded video a single offline source.
    media_sources = html.new_tag("script")
    media_sources.string = """
    for (const slide of document.querySelectorAll('section[data-background-video]')) {
      const source = slide.getAttribute('data-background-video');
      if (!source.startsWith('data:video/')) continue;
      const separator = source.indexOf(',');
      const mime = source.slice(5, source.indexOf(';'));
      const decoded = atob(source.slice(separator + 1));
      const bytes = new Uint8Array(decoded.length);
      for (let i = 0; i < decoded.length; i++) bytes[i] = decoded.charCodeAt(i);
      slide.setAttribute('data-background-video', URL.createObjectURL(new Blob([bytes], {type: mime})));
    }
    """
    initialization = next(tag for tag in html.find_all("script")
                          if tag.string and "Reveal.initialize({" in tag.string)
    initialization.insert_before(media_sources)
    destination.write_text(str(html))
    print(f"Ready: milestone2.html — 17 script slides, {len(sections)} animation stages.")


if __name__ == "__main__":
    main()
