# Claim Adjudication — SGN 6d, Steganalysis Detection

**Status:** adjudication complete. **No manuscript text has been edited. No published
number has been corrected. No detection rate has been made a repair target.**
**Branch:** `master` (this repository's audit work is on `master`; the 6b/6c repairs
are `c143de1`, `6edfd5c`, `8405dd5`).
**Evidence:** `FALSIFIER-LOG-6d.md`.

This closes the one item the sweep deliberately left open. It does **not** close SGN:
6b (LSB round-trip identity) and 6c (execution provenance) were repaired in a previous
session and are not re-audited here.

---

## 1. What was fixed before any number was read

The falsifier's ordering was: definition → population → **classifier-free ground
truth** → reported detector → **emission diagnostic** → comparison → provenance. No
published detection figure was read until step 7.

That ordering changed the conclusion twice, and both corrections are load-bearing
rather than cosmetic:

- The first hypothesis — *the detector is blind to a plainly present signal* — is
  **half false**. A classical chi-square attack also fails. At 10% coverage with a
  **random** payload, blind detection is not achievable here.
- The retraction of that hypothesis then **over-corrected**: the same chi-square
  detector reads 0.35 at `n_images=30` and 0.6000 at `n_images=10`. That is estimator
  variance, not detectability.

The surviving conclusion is narrower than the one first hypothesised, and it is the one
the evidence supports.

---

## 2. Adjudication matrix

| ID | Claim | Source | Verdict | Class |
|---|---|---|---|---|
| C1 | `tab:detection` rates 0.85 / 0.78 / 0.68 / 0.72 | `paper/en/main.tex:223-226` | **CONTRADICTED by the artifact**, which records 0.45 / 0.45 / 0.50 / 0.50 and reproduces exactly through `main()` | R3 |
| C2 | "LSB at 1 bpc is detected with 85% accuracy" | `:212` | **CONTRADICTED** — 0.45 | R3 |
| C3 | "a random forest classifier (**50 trees**) trained on raw pixel patches and **pixel-difference features**" | `:212` | **CONTRADICTED** — that is `SimpleSteganalysis` (line 638, diff features at 604-610). `plot_detection_rate` uses **30 trees** (line 930) on a channel-mean patch and never references `SimpleSteganalysis`. The manuscript describes a detector the reported figure does not use. | R3 |
| C4 | `95% CI` column ±0.06 / ±0.07 / ±0.08 / ±0.07 | `:223-226` | **NO CODE PATH.** `plot_detection_rate` returns `np.mean(cross_val_score(...))`. No interval, standard error or 1.96 construction exists in `sgn_simulator.py`. | R3 |
| C5 | "The GAN-inspired method achieves the lowest detection rate (68%), confirming that learned perturbation patterns are harder to distinguish from natural image statistics" | `:212`, `:246` | **NOT SUPPORTED.** In the artifact all four arms sit at 0.45-0.50, so no ordering exists to confirm from. Separately, "confirming" rests on one number per arm with no dispersion and no CI code path. | R2 |
| C6 | "LSB offers the highest capacity and simplest implementation but is **most detectable**" | `:240` | **NOT SUPPORTED** — all four arms are indistinguishable in the artifact. | R2 |
| C7 | "The DCT method offers strong detectability at low rates but limited capacity" | `:240` | **PARTIALLY SUPPORTED.** Capacity is supported: DCT embeds 200 of 5000 bits (bpp 0.0041 against LSB's 0.10). Detectability is at 0.45 in the artifact, the **lowest** alongside LSB. | R2 |
| C8 | Conclusion: GAN "steganalysis detection rate of 68%" | `:246` | **CONTRADICTED** — 0.50 in the artifact. | R3 |
| C9 | The four detection arms are stego images | implied by `detection_resistance_test` | **UNVERIFIED for two arms.** LSB and DCT decode at 1.000000. GAN_Enc decodes at 0.500073 having modified 40798 values with max diff 12; Adaptive_JND at 0.499140. Their payloads cannot be confirmed. | **R1/R2** |
| C10 | The artifact's detection block is reproducible | — | **PARTIALLY.** Exactly through `main()`. **Not** from an isolated `detection_resistance_test()` call: `main():1048` overrides `n_images` to 10 against a default of 30, and four unrelated experiments have already consumed the module-level `rng`. | R3 |
| C11 | The README's Bit Acc column is honest | `README.md:20-25` | **SUPPORTED** — it reports 0.50 and 0.51 for the two arms whose payloads are unverifiable, which is the truth. | — |
| C12 | 0.45 / 0.45 / 0.50 / 0.50 reflects a broken instrument | — | **NON-FINDING.** Blind detection genuinely fails at this configuration. The values are a plausible measurement. No repair target exists here. | — |

**Counts:** CONTRADICTED 4 · NO CODE PATH 1 · NOT SUPPORTED 2 · PARTIALLY SUPPORTED 1
· UNVERIFIED 1 · PARTIALLY REPRODUCIBLE 1 · SUPPORTED 1 · NON-FINDING 1.

---

## 3. The two findings that matter most

**C9 — two of four arms have no verifiable ground truth.** This is the one finding in
6d that a repair could actually address, and it is not a naming problem. GAN_Enc
modifies 83% of the image with a maximum perturbation of 12 and its decoder recovers
the payload at chance; Adaptive_JND modifies 2478 values and also recovers at chance.
Whether that is a decoder defect (the LSB decoder had exactly this defect before 6b)
or an encoder that does not embed what it claims cannot be settled from this
repository. **The README reports the resulting Bit Acc honestly**, so the document does
not conceal it — but `tab:detection` is computed over arms whose embedded content is
unconfirmed, and nothing in the paper says so.

**C3 — the described detector is not the used detector.** The manuscript describes
50 trees on pixel-difference features. That is `SimpleSteganalysis`. The figure comes
from a 30-tree classifier on a channel-mean grayscale patch. This is the same shape as
the i01 `NoRL` finding: **the document describes a plausible mechanism adjacent to a
number, and the number comes from something else.** Unlike i01, here the repository
does contain the described detector — it is simply not the one used for the figure,
which makes the mismatch more consequential rather than less.

---

## 4. What was corrected in my own working state

My session note recorded the published detection figures as `0.85 / 0.78 / 0.68 / 0.72`
and attributed them to the **README**. **The attribution was wrong.** Verified across
every commit in the history: the README's detect-rate column first exists at `6edfd5c`
reading 0.45 / 0.45 / 0.50 / 0.50, and the two earlier commits have no table at all.
`tools/reconcile_readme.py` regenerates that table from the artifact.

The 0.85-series is in `paper/en/main.tex:223-226`, and 0.85 also appears in both
presentation decks. **The live discrepancy is paper versus artifact, not README versus
artifact** — and the README was brought into line in a previous session while the paper
was not.

Had this note been carried forward unverified, the audit would have reported a resolved
discrepancy as an open one.

---

## 5. Non-findings — protected

| ID | Non-finding | Why it must not be promoted |
|---|---|---|
| N1 | The artifact's near-chance rates are **plausible**, not errors | Blind detection genuinely fails at 10% coverage with a random payload. A repair that tuned these rates toward the published 0.85 would be repairing a target, not a property. |
| N2 | The README already discloses the two unverifiable arms | C11. The document is honest about Bit Acc; only `tab:detection` proceeds as if the arms were confirmed. |
| N3 | 6b and 6c are repaired and not re-audited here | The LSB round-trip identity and the execution provenance block were fixed in `c143de1` and `6edfd5c`. Re-opening them is out of scope for 6d. |
| N4 | The chi-square reading of 0.35 vs 0.60 proves nothing about detectability | It is estimator variance at 4 samples per class per fold. It must not be cited as evidence that the attack works or fails. |

---

## 6. Repair classes

| Class | Items | Meaning |
|---|---|---|
| **R1** | C9 | Two decoders (or two encoders) do not round-trip their own payload. Diagnosable, and the 6b falsifier is the template. |
| **R2** | C5, C6, C7 | Comparative claims about detectability cannot be settled by arms at chance with two of four unverified. No detector change is authorised; the arms must be made verifiable first. |
| **R3** | C1, C2, C3, C4, C8, C10 | Numbers, the described detector, the CI column, and the isolation-reproducibility gap. **No code change** for C1-C4 and C8. |

**No repair is authorised.** C9 is the only candidate, and repairing it changes numbers
that four published claims depend on — so it is a decision about the manuscript, not
an engineering task.

---

## 7. Summary

| | |
|---|---|
| Claims adjudicated | 12 |
| CONTRADICTED | 4 |
| NO CODE PATH | 1 |
| NOT SUPPORTED | 2 |
| PARTIALLY SUPPORTED / PARTIALLY REPRODUCIBLE | 2 |
| UNVERIFIED (the substantive finding) | 1 |
| SUPPORTED | 1 |
| **NON-FINDING** | 1 |
| Non-findings protected | 4 |
| Falsifier defects retained | 4 |
| Hypotheses retracted | 2 (one of them a retraction of the first retraction) |

**SGN 6d is adjudicated.** With it, the last item the sweep left deliberately open is
closed. The P1 backlog is now six packages closed and no open items.

The headline of 6d is not the detection rates. It is that **two of four arms have no
verifiable ground truth**, and that the manuscript describes a detector the reported
figure does not use.