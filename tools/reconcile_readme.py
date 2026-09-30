"""Render the published SGN results table from the committed artifact.

Row 6b of P1-REPAIR-SPEC-v1.0. The published table in README.md must be a
projection of figures/metrics.json and nothing else, so that every value a
reader sees is traceable to a run.

    simulator -> figures/metrics.json -> this module -> README table

tests/test_provenance.py asserts that the table currently in README.md equals
what this module renders, which is what makes a hand-edited value detectable.

Run directly to rewrite the table in place:

    python tools/reconcile_readme.py --write
"""

import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
METRICS = os.path.join(ROOT, "figures", "metrics.json")
README = os.path.join(ROOT, "README.md")

HEADER = (
    "| Method | Domain | PSNR (dB) | SSIM | bpp | Bit Acc | Detect Rate |\n"
    "|---|---|---|---|---|---|---|\n"
)

# Domain and detect-rate labels are editorial, not measured. They are declared
# here rather than in the README so that the generated block is a complete
# function of the artifact plus this table, and any drift is visible in one
# place.
DOMAIN = {
    "LSB": "Spatial",
    "DCT": "Transform",
    "GAN_Enc": "Latent",
    "Adaptive_JND": "Spatial+JND",
}


def _detect_rate(metrics, method):
    detection = metrics.get("detection", {}).get(method)
    if detection is None:
        return "—"
    return f"{float(detection):.2f}"


def table_markdown(metrics):
    """Render the published table from a parsed artifact."""
    summary = metrics.get("summary")
    if not summary:
        raise SystemExit(
            "artifact has no 'summary' block; refusing to render a table from "
            "method names alone"
        )

    rows = []
    for method in metrics["methods"]:
        entry = summary[method]
        rows.append(
            "| {label} | {domain} | {psnr} | {ssim} | {bpp} | {acc} | {det} |".format(
                label=method,
                domain=DOMAIN.get(method, "—"),
                psnr=f"{entry['psnr_db']:.1f}",
                ssim=f"{entry['ssim']:.3f}",
                bpp=("{:.4f}".format(entry["bpp"])
                     if entry["bpp"] < 0.01 else "{:.2f}".format(entry["bpp"])),
                acc=f"{entry['bit_accuracy']:.2f}",
                det=_detect_rate(metrics, method),
            )
        )
    return HEADER + "\n".join(rows) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite the table block in README.md from the artifact",
    )
    args = parser.parse_args()

    with open(METRICS) as handle:
        metrics = json.load(handle)

    rendered = table_markdown(metrics)

    if not args.write:
        sys.stdout.write(rendered)
        return 0

    with open(README) as handle:
        body = handle.read()

    lines = body.splitlines(keepends=True)
    start = end = None

    for i, line in enumerate(lines):
        if line.startswith("| Method |") and "Bit Acc" in line:
            start = i
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            end = j
            break

    if start is None:
        raise SystemExit("no results table found in README.md; nothing written")

    # Replace exactly the header, separator and data rows, once. An earlier
    # version of this function spliced the rendered block into `out` and then
    # indexed `out` with a line number, which emitted the table twice. A second
    # copy in the file made a hand-edited value undetectable, because the
    # original text still satisfied the comparison.
    new_lines = lines[:start] + [rendered] + lines[end:]

    with open(README, "w") as handle:
        handle.write("".join(new_lines))

    print(
        f"README.md results table regenerated from figures/metrics.json "
        f"(replaced lines {start + 1}-{end})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
