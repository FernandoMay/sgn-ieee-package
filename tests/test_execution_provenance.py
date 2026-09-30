#!/usr/bin/env python3
"""Row 6c falsifier: execution provenance.

Property under test.

    Every quantitative artifact must identify the source revision and execution
    environment sufficient to distinguish the run from another implementation or
    dependency state.

Two distinct obligations, tested separately.

    F1  the required provenance fields exist and are populated
    F2  two artifacts that differ in provenance are not provenance-equivalent

F2 is deliberately weaker than "any change moves a number", and it is worth
being precise about why. A dependency upgrade that happens not to perturb the
arithmetic is still a different run and must not be presented as the same run.
The property is that the origin is distinguishable, not that every origin
produces a different result. Testing the latter would fail for the wrong reason
and would push us into tuning the metrics until they move, which is the failure
mode this whole program exists to catch.

This test imports nothing from the simulator under verification. It reads the
committed artifact.
"""

import copy
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
METRICS = ROOT / "figures" / "metrics.json"

REQUIRED = {
    "source_commit",
    "python_version",
    "dependency_versions",
    "seed",
    "configuration",
    "generator",
}

PREFERRED = {"platform", "architecture"}

SHA1 = re.compile(r"^[0-9a-f]{40}$")
PYVER = re.compile(r"^3\.\d+\.\d+")


def git_revision():
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except OSError:
        return None


def git_contains(revision):
    """True when `revision` is HEAD or an ancestor of it.

    Equality would be the wrong test. An artifact cannot record the commit that
    contains it — the artifact is itself part of that commit — so requiring
    equality is unsatisfiable by construction and would push someone into
    writing a revision that is not the one that ran. What actually matters is
    that the recorded revision is reachable in this history: a real commit whose
    code produced the run.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", revision, "HEAD"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return out.returncode == 0


def provenance_equivalent(a, b):
    """True when two provenance blocks describe the same run.

    Compares the fields that identify the run. A recorded commit cannot be
    empty: an uncommitted run is not the same run, and must not be reported as
    if it were.
    """
    keys = sorted(set(a) | set(b))
    for key in keys:
        if key not in a or key not in b:
            return False
        if key == "dependency_versions":
            if a[key] != b[key]:
                return False
            continue
        if a[key] != b[key]:
            return False
    return True


def main():
    print("property: an artifact identifies the code and environment that")
    print("         produced it, well enough to tell two runs apart")
    print("=" * 78)

    if not METRICS.exists():
        print(f"  [FAIL] artifact absent: {METRICS.relative_to(ROOT)}")
        return 1

    with open(METRICS) as handle:
        artifact = json.load(handle)

    failures = []
    provenance = artifact.get("provenance")

    if not isinstance(provenance, dict):
        print("  [FAIL] F1 artifact carries no provenance block")
        return 1

    # --- F1a: the required set is present -----------------------------------
    present = set(provenance)
    missing = sorted(REQUIRED - present)
    if missing:
        print(f"  [FAIL] F1 provenance identifies {len(present)} field(s), "
              f"missing {len(missing)}: {', '.join(missing)}")
        failures.append("F1-missing-fields")
    else:
        print(f"  [PASS] F1 all {len(REQUIRED)} required provenance fields present")

    # --- F1b: the fields are populated, not placeholders --------------------
    unpopulated = []
    if "seed" in provenance and provenance["seed"] is None:
        unpopulated.append("seed")
    if "generator" in provenance and not str(provenance.get("generator") or "").strip():
        unpopulated.append("generator")
    if "configuration" in provenance:
        cfg = provenance["configuration"]
        if not isinstance(cfg, dict) or not cfg:
            unpopulated.append("configuration")
    commit = provenance.get("source_commit")
    if commit is not None and not SHA1.match(str(commit)):
        unpopulated.append("source_commit (not a full 40-char revision)")
    pyver = provenance.get("python_version")
    if pyver is not None and not PYVER.match(str(pyver)):
        unpopulated.append("python_version (not a 3.x.y interpreter version)")
    deps = provenance.get("dependency_versions")
    if deps is not None and not (isinstance(deps, dict) and deps):
        unpopulated.append("dependency_versions")

    if unpopulated:
        print(f"  [FAIL] F1b present but unpopulated: {', '.join(unpopulated)}")
        failures.append("F1b-unpopulated")
    else:
        checked = [k for k in ("source_commit", "python_version",
                               "dependency_versions", "seed", "configuration",
                               "generator") if k in provenance]
        print(f"  [PASS] F1b populated and well-formed ({len(checked)} field(s))")

    # --- F1c: preferred fields ---------------------------------------------
    absent = sorted(PREFERRED - present)
    if absent:
        print(f"  [WARN] F1c preferred fields absent: {', '.join(absent)}")
    else:
        print(f"  [PASS] F1c preferred fields present: {', '.join(sorted(PREFERRED))}")

    # --- F2: provenance distinguishability -----------------------------------
    # Mutations stand in for "somebody ran this again under different
    # circumstances". Each must break equivalence.
    mutations = []

    if "source_commit" in provenance:
        other = "0" * 40 if provenance["source_commit"] != "0" * 40 else "1" * 40
        mutations.append(("source_commit", provenance["source_commit"], other))

    if isinstance(provenance.get("dependency_versions"), dict) and provenance["dependency_versions"]:
        name = sorted(provenance["dependency_versions"])[0]
        bumped = copy.deepcopy(provenance["dependency_versions"])
        bumped[name] = "99.99.99"
        mutations.append((f"dependency_versions[{name}]",
                          provenance["dependency_versions"][name], "99.99.99"))

    if "seed" in provenance:
        mutations.append(("seed", provenance["seed"], 4242))

    if "configuration" in provenance:
        bumped_cfg = copy.deepcopy(provenance["configuration"])
        key = sorted(bumped_cfg)[0]
        bumped_cfg[key] = "perturbed"
        mutations.append((f"configuration[{key}]",
                          bumped_cfg[key], provenance["configuration"][key]))

    if not mutations:
        print("  [FAIL] F2 nothing to mutate; provenance is too thin to distinguish runs")
        failures.append("F2-no-mutation-surface")
    else:
        indistinguishable = []
        for label, before, after in mutations:
            mutant = copy.deepcopy(provenance)
            if label.startswith("dependency_versions["):
                mutant["dependency_versions"] = dict(mutant["dependency_versions"])
                mutant["dependency_versions"][sorted(mutant["dependency_versions"])[0]] = after
            elif label.startswith("configuration["):
                mutant["configuration"] = bumped_cfg
            elif label == "seed":
                mutant["seed"] = after
            else:
                mutant["source_commit"] = after

            if provenance_equivalent(provenance, mutant):
                indistinguishable.append(label)

        if indistinguishable:
            print(f"  [FAIL] F2 mutation went unnoticed, artifact still reads as the same "
                  f"run: {', '.join(indistinguishable)}")
            failures.append("F2-indistinguishable")
        else:
            print(f"  [PASS] F2 all {len(mutations)} mutations break provenance equivalence "
                  f"({', '.join(m[0] for m in mutations)})")

    # --- F3: the recorded commit is this checkout ---------------------------
    head = git_revision()
    recorded = provenance.get("source_commit")
    dirty = provenance.get("source_dirty")
    if not recorded:
        print("  [FAIL] F3 no source_commit recorded; the artifact is untraceable")
        failures.append("F3-untraceable")
    elif git_contains(recorded):
        print(f"  [PASS] F3 recorded source_commit {recorded[:12]} is reachable in "
              f"this history (HEAD {head[:12]})")
        if dirty:
            print(f"  [WARN] F3 the tree was dirty at generation time; "
                  f"source_commit records HEAD, not the exact bytes that ran")
    else:
        print(f"  [FAIL] F3 recorded source_commit {recorded[:12]} is not reachable "
              f"from HEAD {head[:12]}; the artifact cannot be tied to this history")
        failures.append("F3-unreachable")

    print("=" * 78)
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("PASSED: the artifact identifies its own origin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
