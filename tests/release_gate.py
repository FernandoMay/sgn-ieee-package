#!/usr/bin/env python3
"""Release gate for SGN 6d.

Ordered pipeline
    DESTINATION -> LINEAGE -> FALSIFIER -> GROUND TRUTH -> EMISSION
    -> ADJUDICATION -> NON-FINDING NEGATIONS -> PROHIBITIONS -> CLEAN TREE

The prohibitions are verified by REJECTING their violation. Each exists because this
falsifier or a previous one in this sweep actually made that mistake:

  P1  no published number as a repair target
  P2  the near-chance artifact rates are plausible measurements, not errors
  P3  chi-square 0.35 vs 0.60 is estimator variance, not a detectability finding
  P4  the 0.85-series is the PAPER, not the README; the README was already corrected
  P5  a retracted hypothesis must not reappear as a finding
  P6  the narrative must not contradict the measurement column beside it
"""
import os, re, sys, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PYTHON = os.environ.get("PYTHON", "python3")
ADJ = os.path.join(ROOT, "CLAIM-ADJUDICATION-6d.md")
LOG = os.path.join(ROOT, "FALSIFIER-LOG-6d.md")
FALSIFIER = "test_detection_groundtruth.py"

NON_FINDINGS = [
    ("N1", "the artifact's near-chance rates are plausible, not errors",
     [r"plausible measurement"]),
    ("N2", "the README already discloses the unverifiable arms",
     [r"README reports their Bit Acc honestly"]),
    ("N3", "6b and 6c are repaired and not re-audited here",
     [r"not re-audited here"]),
    ("N4", "chi-square 0.35 vs 0.60 is estimator variance",
     [r"estimator variance"]),
]

PROHIBITIONS = [
    ("P1", "no published number is a repair target",
     [r"No detection rate has been made a repair target",
      r"would be repairing a target, not a property"]),
    ("P2", "the near-chance rates are not errors",
     [r"tuned these rates toward the published 0\.85"]),
    ("P3", "the chi-square reading is not a detectability finding",
     [r"must not be cited as evidence"]),
    ("P4", "the 0.85-series is the paper, not the README",
     [r"paper versus artifact, not README versus artifact"]),
    ("P5", "retracted hypotheses must not reappear as findings",
     [r"Hypotheses retracted"]),
    ("P6", "narrative must not contradict the measurement beside it",
     [r"fourth occurrence in this sweep|fourth such occurrence"]),
]


def run():
    try:
        p = subprocess.run([PYTHON, os.path.join(HERE, FALSIFIER)],
                           capture_output=True, text=True, cwd=ROOT, timeout=3600)
    except subprocess.TimeoutExpired:
        return None, ""
    return p.returncode, p.stdout + p.stderr


def main():
    print("=" * 78)
    print("SGN 6d release gate")
    print("  DESTINATION -> LINEAGE -> FALSIFIER -> GROUND TRUTH -> EMISSION ->")
    print("  ADJUDICATION -> NON-FINDING NEGATIONS -> PROHIBITIONS -> CLEAN TREE")
    print("=" * 78)
    failures = []
    stage = lambda n: print(f"\n  --- {n} ---")

    stage("DESTINATION")
    log = subprocess.run(["git", "log", "--oneline", "-3"], cwd=ROOT,
                         capture_output=True, text=True).stdout
    print(log.strip())
    if not log.strip():
        failures.append("no git history")

    stage("FALSIFIER + GROUND TRUTH + EMISSION")
    rc, out = run()
    n_fail = len(re.findall(r"^\s*\[FAIL\]", out, re.M))
    n_pass = len(re.findall(r"^\s*\[PASS\]", out, re.M))
    ok = rc is not None and rc == 1 and n_fail > 0 and n_pass > 0
    print(f"  [{'OK' if ok else 'PROBLEM':7s}] {FALSIFIER}  exit={rc} "
          f"FAIL={n_fail} PASS={n_pass}")
    for needle, label in ((r"bit accuracy", "classifier-free ground truth reported"),
                          (r"oracle separates", "emission diagnostic present"),
                          (r"EMISSION", "emission step precedes conclusions")):
        present = re.search(needle, out) is not None
        print(f"  [{'OK' if present else 'PROBLEM':7s}] {label}")
        if not present:
            failures.append(f"falsifier output missing: {label}")
    if not ok:
        failures.append("falsifier did not behave as RED-with-passing-control")

    stage("ADJUDICATION")
    if os.path.exists(ADJ):
        adj = re.sub(r"\s+", " ", open(ADJ, encoding="utf-8").read())
        for label, pat in (
            ("two of four arms lack verifiable ground truth", r"no verifiable ground truth"),
            ("described detector is not the used detector",
             r"described detector is not the used detector"),
            ("CI column has no code path", r"NO CODE PATH"),
            ("correction of the stale README attribution",
             r"attributed them to the \*\*README\*\*"),
            ("narrower conclusion than hypothesised",
             r"narrower than the one first hypothesised"),
        ):
            hit = re.search(pat, adj) is not None
            print(f"  [{'OK' if hit else 'PROBLEM':7s}] {label}")
            if not hit:
                failures.append(f"adjudication missing: {label}")
    else:
        print("  [PROBLEM] adjudication missing")
        failures.append("adjudication-missing")

    stage("NON-FINDING NEGATIONS")
    adj = re.sub(r"\s+", " ", open(ADJ, encoding="utf-8").read()) if os.path.exists(ADJ) else ""
    logtext = re.sub(r"\s+", " ", open(LOG, encoding="utf-8").read()) if os.path.exists(LOG) else ""
    both = adj + " " + logtext
    for tag, label, pats in NON_FINDINGS:
        missing = [p for p in pats if re.search(p, both) is None]
        print(f"  [{'OK' if not missing else 'PROBLEM':7s}] {tag} {label}")
        for m in missing:
            print(f"             - missing or reversed: {m!r}")
        if missing:
            failures.append(f"non-finding lost: {tag}")

    stage("PROHIBITIONS")
    for tag, label, pats in PROHIBITIONS:
        missing = [p for p in pats if re.search(p, both) is None]
        print(f"  [{'OK' if not missing else 'PROBLEM':7s}] {tag} {label}")
        for m in missing:
            print(f"             - not stated: {m!r}")
        if missing:
            failures.append(f"prohibition not stated: {tag}")
    # P7 negative test: the near-chance values must NOT be presented as errors
    # P7, checked ROW BY ROW rather than by regex over whitespace-collapsed text.
    # The regex version flagged the adjudication's own C12 row: its CLAIM cell reads
    # "reflects a broken instrument" and its VERDICT cell reads NON-FINDING two
    # columns to the right, which no bounded regex can see. Line-scoped inspection
    # reads the whole row at once, which is what the reader does.
    raw_adj = open(ADJ, encoding="utf-8").read() if os.path.exists(ADJ) else ""
    rows = [l for l in raw_adj.split("\n") if l.strip().startswith("|")]
    violation, refuted = None, False
    for row in rows:
        has_rate = ("0.45" in row) or ("0.50" in row)
        asserts_bad = any(t in row for t in
                          ("broken instrument", "is wrong", "is incorrect",
                           "is an error", "must be corrected"))
        has_refutation = "NON-FINDING" in row or "NON-FINDING" in row.replace("**", "")
        if has_rate and asserts_bad:
            if has_refutation:
                refuted = True          # asserted and refuted in the same row
            else:
                violation = row.strip()
                break
    print(f"  [{'OK' if not violation else 'PROBLEM':7s}] P7 near-chance values are never "
          f"asserted to be wrong")
    if violation:
        print(f"             - unrefuted violation: {violation!r}")
        failures.append("P7 near-chance values asserted to be wrong")
    print(f"  [{'OK' if refuted else 'PROBLEM':7s}] P7b the near-chance claim carries an "
          f"explicit NON-FINDING verdict")
    if not refuted:
        failures.append("P7b near-chance claim not explicitly refuted")

    stage("CLEAN TREE")
    st = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                        capture_output=True, text=True).stdout
    # The gate's own log is written by this run and is not a change to the audited
    # object. Excluding it is stated, not silent, so the exclusion is auditable.
    own = {"GATE-LOG-6d.md"}
    residue = [l for l in st.split("\n")
               if l.strip() and l.split(maxsplit=1)[-1] not in own]
    if any(l.split(maxsplit=1)[-1] in own for l in st.split("\n") if l.strip()):
        print(f"             (ignored the gate's own output: {sorted(own)})")
    print(f"  [{'OK' if not residue else 'PROBLEM':7s}] clean: {not residue}")
    for l in residue:
        print(f"             {l}")
    # This stage previously PRINTED a problem without appending to `failures`, so the
    # gate could report GATE PASSED while its own tree stage showed PROBLEM. A stage
    # that cannot fail the gate is decoration, and a green gate whose last line is red
    # teaches a reader to trust the wrong line.
    if residue:
        failures.append(f"working tree not clean: {len(residue)} path(s)")

    print("\n" + "=" * 78)
    if failures:
        print(f"GATE FAILED — {len(failures)} problem(s):")
        for f in failures:
            print(f"  {f}")
        return 1
    print("GATE PASSED")
    print("\nNO MANUSCRIPT TEXT EDITED. NO PUBLISHED NUMBER CORRECTED.")
    print("NO DETECTION RATE MADE A REPAIR TARGET.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
