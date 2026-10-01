==============================================================================
SGN-6d falsifier — what does the detection-rate column measure?
property: the reported detection rate measures detectability of the payload
==============================================================================

  [INFO] 1-2. definition and population
         'Detection' = 5-fold CV accuracy of a random forest separating cover
         from stego images. PAIRED: each stego derives from a known cover.
         main() calls detection_resistance_test(n_images=10) at line 1048,
         overriding the function's default of 30.

  [INFO] 3. GROUND TRUTH independent of any classifier (decode the payload)
         method          bit accuracy   values changed   payload verifiable?
         LSB                 1.000000             2502                   YES
         DCT                 1.000000             1165                   YES
         GAN_Enc             0.500073            40798                    NO
         Adaptive_JND        0.499140             2478                    NO
         methods whose payload is verifiably present: ['LSB', 'DCT']
         GAN_Enc and Adaptive_JND modify 40798 and 2478 values respectively
         yet their decoders recover the payload at CHANCE. Their detection
         arms are therefore labelled from images whose payload cannot be
         verified. The README reports their Bit Acc honestly as 0.50 / 0.51.

  [INFO] 4. the reported detector, on the same population (n_images=10)
         LSB            0.5000
         DCT            0.5500
         GAN_Enc        0.5000
         Adaptive_JND   0.5000

  [INFO] 5. EMISSION — is there a signal where the blind detectors look?
         values changed by LSB encode: 2527 of 49152 (5.14%)
         inside the 1024-value detector window: 701 changed
         signal in that window: 1.000000   natural std: 14.3269   ratio 0.0698

  [INFO] 6. blind detectors compared on identical data
  method          reported feats   lsb-plane   chi-square
  LSB                     0.5000      0.5000       0.6000
  DCT                     0.5500      0.5000            -
  GAN_Enc                 0.5000      0.3500            -
  Adaptive_JND            0.5000      0.4500            -

         range across all blind detectors and methods: 0.3500 to 0.6000
         detectors above 0.55: [('LSB', 'chi-square', 0.6)]
         n_images=10 means 20 samples for cv=5, i.e.
         4 samples per class per fold. One sample moving across a
         fold boundary moves that fold by 0.2500, so any single
         detector's score at this sample size is not a stable quantity.

         CORRECTION, and it corrects an earlier correction. An earlier working
         hypothesis said the signal was plainly present and only the feature
         set was blind. That was then partly retracted on the strength of a
         chi-square score of 0.35 at n_images=30. Measured HERE at
         n_images=10 the chi-square scores 0.6000.
         The same detector therefore reads 0.35 and 0.60 at two sample sizes, which is a statement
         about the estimator's variance and not about detectability.

         WHAT SURVIVES, and it is the only part that is load-bearing:
           - the payload is verifiably present for LSB and DCT (bit accuracy
             1.000000, established by decoding with no classifier involved);
           - an oracle given the paired cover separates 10/10, so the signal
             is inside the window every blind detector reads;
           - consequently blind detection fails here because the perturbation
             is small relative to natural variance, NOT because nothing was
             embedded.
         The artifact's near-chance numbers are therefore a PLAUSIBLE
         measurement at this configuration. No claim is made that they are
         the right ones.

  [INFO] CONTROL C1 — an oracle given the paired cover must reach 1.0.
         This is what proves the signal exists where the blind detectors look.
         oracle separates 10/10 pairs; 7097 changed values inside the detector window
  [PASS] C1 the signal is present inside the window every blind detector reads.
         Blind detection fails because the perturbation is small relative to
         natural variance, NOT because nothing was embedded.

  [INFO] 7. artifact provenance
         artifact detection block: {"LSB": 0.45, "DCT": 0.45, "GAN_Enc": 0.5, "Adaptive_JND": 0.5}
         an ISOLATED run at n_images=10 reproduces it: False
         The committed artifact is reproducible only through main(),
         where four unrelated experiments have already consumed the
         module-level RNG and n_images is 10 rather than the default 30.
         A reader invoking detection_resistance_test() directly gets a
         different number. That is a reproducibility defect, not a
         disagreement about the value.

  [INFO] 8. the detector the manuscript describes vs the one used
         paper/en/main.tex:212 — 'random forest classifier (50 trees,
         5-fold cross-validation) trained on raw pixel patches and
         pixel-difference features'.
         n_estimators=50 at line(s) [638]  -> SimpleSteganalysis, which has
           the pixel-difference features the manuscript describes
         n_estimators=30 at line(s) [930]  -> plot_detection_rate, which
           produces the figure and uses a channel-mean grayscale patch
         plot_detection_rate does not reference SimpleSteganalysis at all.
         The manuscript describes a detector the reported figure does not
         use.

         the manuscript's '95% CI' column (+-0.06/0.07/0.08/0.07) has a
         code path: False
==============================================================================
FAILED: SGN-6d-ground-truth-unverified-for-GAN_Enc-Adaptive_JND, SGN-6d-not-reproducible-in-isolation, SGN-6d-described-detector-is-not-the-one-used, SGN-6d-ci-column-has-no-code-path

## Hypotheses this falsifier had to retract, and how

**H1 (retracted, partly).** "The reported detector is blind to a signal that is
plainly present, so the near-chance number is an instrument artifact."

The first half survives. The second half does not. A classical chi-square attack for
LSB replacement — the textbook detector for exactly this embedding — was run on the
same images and did not separate them. The embedding occupies 5.14% of values, the
oracle finds it in 10/10 pairs, and no blind statistic finds it, because 10% coverage
with a RANDOM payload perturbs the paired histogram by roughly 5 units against a
within-class standard deviation of 25.

**H2 (retracted, then re-retracted).** After the chi-square read 0.35 at
`n_images=30`, I retracted part of H1 and wrote "every blind detector is at or below
chance, including the chi-square attack". Measured at `n_images=10` — the
configuration `main()` actually uses — the same detector reads **0.6000**.

The same detector scores 0.35 and 0.60 at two sample sizes. That is a fact about the
estimator's variance, not about detectability. At n=10 there are 20 samples for 5-fold
CV, so 4 per class per fold, and one sample crossing a fold boundary moves that fold by
0.25. No single detector's score at this sample size is a stable quantity, in either
direction.

**What survives, and it is the only load-bearing part:**

1. The payload is **verifiably present** for LSB and DCT — bit accuracy 1.000000,
   established by decoding with no classifier involved.
2. An **oracle** given the paired cover separates 10/10 pairs, with 7097 changed values
   inside the detector window. The signal is where the blind detectors look.
3. Therefore blind detection fails here because the perturbation is small relative to
   natural variance, **not** because nothing was embedded.

The artifact's near-chance numbers are a **plausible measurement at this
configuration**. No claim is made that they are the right ones. That is a narrower
statement than the one I set out to test, and it is the one the evidence supports.

## New findings this falsifier produced

**F1 — Ground truth is unverified for two of four methods.**

| method | bit accuracy | values changed | payload verifiable? |
|---|---|---|---|
| LSB | 1.000000 | 2502 | **YES** |
| DCT | 1.000000 | 1165 | **YES** |
| GAN_Enc | 0.500073 | 40798 | **NO** |
| Adaptive_JND | 0.499140 | 2478 | **NO** |

GAN_Enc modifies 40798 of 49152 values (83%) with max |diff| 12, and its decoder still
recovers the payload at chance. Adaptive_JND modifies 2478 values with max |diff| 1,
also at chance.

Their detection arms are therefore labelled from images whose embedded content cannot
be confirmed. `README.md` reports their Bit Acc honestly as 0.50 and 0.51, so the
document does not conceal this — but the detection column is computed over arms whose
ground truth is unverified.

**F2 — the artifact is reproducible only through `main()`.**
`main()` at line 1048 calls `detection_resistance_test(n_images=10)`, overriding the
function's default of 30, and four unrelated experiments have already consumed the
module-level `rng`. An isolated invocation at n_images=10 does **not** reproduce the
committed block (0.5000 / 0.5500 / 0.5000 / 0.5000 against 0.45 / 0.45 / 0.50 / 0.50);
a full `main()` run reproduces it exactly. A reader who calls the documented function
gets a different number.

**F3 — the manuscript describes a detector the reported figure does not use.**
`paper/en/main.tex:212` describes "a random forest classifier (50 trees, 5-fold
cross-validation) trained on raw pixel patches and pixel-difference features".

- `n_estimators=50` appears once, at line 638, inside `SimpleSteganalysis`, which does
  compute pixel-difference features at lines 604-610.
- `n_estimators=30` appears once, at line 930, inside `plot_detection_rate`, which
  produces the figure and uses a channel-mean grayscale patch with no difference
  features.
- `plot_detection_rate` does not reference `SimpleSteganalysis` at all.

**F4 — the `95% CI` column has no code path.**
The manuscript's table reports ±0.06, ±0.07, ±0.08, ±0.07. `plot_detection_rate`
returns only `np.mean(cross_val_score(...))`. No confidence interval, standard error
or 1.96 construction exists anywhere in `sgn_simulator.py`. The only `95` in the file
is `np.percentile(np.abs(diff), 95)` inside a feature extractor.

## Correction to my own working notes

My session note recorded "published Detect Rate 0.85 / 0.78 / 0.68 / 0.72 vs
regenerated 0.45 / 0.45 / 0.50 / 0.50" and attributed the published figures to the
README. **The attribution was wrong.** The README table was regenerated from the
artifact by `tools/reconcile_readme.py` in commit `6edfd5c` and has read
0.45 / 0.45 / 0.50 / 0.50 since it first existed. The 0.85 / 0.78 / 0.68 / 0.72 figures
are in `paper/en/main.tex:223-226`, and 0.85 also appears in both presentation decks.
Verified across every commit in the history: the README detect-rate column reads
0.45 0.45 0.50 0.50 at `6edfd5c` and `8405dd5`, and the two earlier commits have no
table at all.

The live discrepancy is therefore **paper versus artifact**, not README versus
artifact — and the README was already brought into line while the paper was not.

## Falsifier defects (all retained)

1. **A narrative contradicting the measurement, twice in one file.** The first draft
   printed "every blind detector is at or below chance, INCLUDING the classical
   chi-square" while the chi-square column on the line above read 0.6000. This is the
   fourth occurrence in this sweep of a hardcoded conclusion printed beside a
   measurement that did not support it, and the second in this file alone. The block
   is now derived from the measured values and prints both sample sizes.
2. **A stale note about the package's own state.** The working note attributed the
   0.85-series to the README. The README never carried those values. The live
   discrepancy is paper-versus-artifact.
3. **Key/value unpacking bug.** `above` held keys only; unpacking each as `(key, value)`
   produced a string where a float was expected, raising `TypeError` twice before the
   display was fixed.
4. **A dead conditional** (`... if False else None`) left in the detector-comparison
   block by an earlier draft.

## Falsifier defects (continued) — what was NOT done

No manuscript text edited. No published number corrected. No detection rate made a
repair target. The near-chance artifact values are recorded as plausible measurements,
not as errors to be tuned toward 0.85.
