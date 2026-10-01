==============================================================================
SGN 6d release gate
  DESTINATION -> LINEAGE -> FALSIFIER -> GROUND TRUTH -> EMISSION ->
  ADJUDICATION -> NON-FINDING NEGATIONS -> PROHIBITIONS -> CLEAN TREE
==============================================================================

  --- DESTINATION ---
38ba3ca test(sgn): gate — P7 row-scoped, and CLEAN TREE can now fail the gate
233de19 test(sgn): 6d adjudication, gate, and RED markers
aadeabd test(sgn): 6d falsifier — ground truth, emission, and two undocumented arms

  --- FALSIFIER + GROUND TRUTH + EMISSION ---
  [OK     ] test_detection_groundtruth.py  exit=1 FAIL=4 PASS=1
  [OK     ] classifier-free ground truth reported
  [OK     ] emission diagnostic present
  [OK     ] emission step precedes conclusions

  --- ADJUDICATION ---
  [OK     ] two of four arms lack verifiable ground truth
  [OK     ] described detector is not the used detector
  [OK     ] CI column has no code path
  [OK     ] correction of the stale README attribution
  [OK     ] narrower conclusion than hypothesised

  --- NON-FINDING NEGATIONS ---
  [OK     ] N1 the artifact's near-chance rates are plausible, not errors
  [OK     ] N2 the README already discloses the unverifiable arms
  [OK     ] N3 6b and 6c are repaired and not re-audited here
  [OK     ] N4 chi-square 0.35 vs 0.60 is estimator variance

  --- PROHIBITIONS ---
  [OK     ] P1 no published number is a repair target
  [OK     ] P2 the near-chance rates are not errors
  [OK     ] P3 the chi-square reading is not a detectability finding
  [OK     ] P4 the 0.85-series is the paper, not the README
  [OK     ] P5 retracted hypotheses must not reappear as findings
  [OK     ] P6 narrative must not contradict the measurement beside it
  [OK     ] P7 near-chance values are never asserted to be wrong
  [OK     ] P7b the near-chance claim carries an explicit NON-FINDING verdict

  --- CLEAN TREE ---
             (ignored the gate's own output: ['GATE-LOG-6d.md'])
  [OK     ] clean: True

==============================================================================
GATE PASSED

NO MANUSCRIPT TEXT EDITED. NO PUBLISHED NUMBER CORRECTED.
NO DETECTION RATE MADE A REPAIR TARGET.
