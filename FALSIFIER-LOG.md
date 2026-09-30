# Falsifier log — SGN round-trip

**Date:** 2026-09-30
**Pre-fix run:** against commit `311f948`, before any change to this repository.
**Interpreter:** `/private/tmp/venv2/bin/python` (numpy, scipy, matplotlib, sklearn all present).

This log is retained as evidence. The pre-fix output is not to be edited after
the repair, and the ~0.50 it records is not to be replaced by 1.0 as though it
were a correction of a number. It is the record of what the published decoder
was actually doing.

## The property under test

```
decode(encode(payload)) == payload        exactly, for any payload and any cover
```

A mathematical identity. It does not depend on the aggregate `bit_accuracy`
figure, on the README table, or on any claim in the paper. A repair of the
codec is accepted when the round trip holds exactly, and not when the reported
accuracy rises.

## Pre-fix result

```
==============================================================================
ROUND-TRIP FALSIFIER — LSBSteganography
property: decode(encode(payload)) == payload, exactly
==============================================================================
  [FAIL] random-seed1: n=5000 embedded=5000 recovered=393216 bit_accuracy=0.4990
  [FAIL] random-seed2: n=5000 embedded=5000 recovered=393216 bit_accuracy=0.5016
  [FAIL] random-seed3: n=5000 embedded=5000 recovered=393216 bit_accuracy=0.5078
  [FAIL] random-seed7: n=5000 embedded=5000 recovered=393216 bit_accuracy=0.4992
  [FAIL] random-seed11: n=5000 embedded=5000 recovered=393216 bit_accuracy=0.4908
  [FAIL] len1: n=1 embedded=1 recovered=393216 bit_accuracy=0.0000
  [FAIL] len7: n=7 embedded=7 recovered=393216 bit_accuracy=0.4286
  [FAIL] len9: n=9 embedded=9 recovered=393216 bit_accuracy=0.4444
  [FAIL] len13: n=13 embedded=13 recovered=393216 bit_accuracy=0.4615
  [FAIL] len101: n=101 embedded=101 recovered=393216 bit_accuracy=0.4455
  [FAIL] len999: n=999 embedded=999 recovered=393216 bit_accuracy=0.4925
  [FAIL] len1001: n=1001 embedded=1001 recovered=393216 bit_accuracy=0.4935
  [PASS] all-zeros: n=5000 embedded=5000 recovered=393216 bit_accuracy=1.0000
  [FAIL] all-ones: n=5000 embedded=5000 recovered=393216 bit_accuracy=0.1250
  [FAIL] alternating-0101: n=5000 embedded=5000 recovered=393216 bit_accuracy=0.5624
  [FAIL] len-equals-capacity: n=49152 embedded=49152 recovered=393216 bit_accuracy=0.5011
  [FAIL] bpc2-len4000: n=4000 embedded=4000 recovered=393216 bit_accuracy=0.4885
  [FAIL] bpc3-len4000: n=4000 embedded=4000 recovered=393216 bit_accuracy=0.5080
------------------------------------------------------------------------------
FAILED: 17 of 18 cases
```

## What the failure pattern establishes

Three readings from the pre-fix output, each of which pins the mechanism.

**1. The output length is independent of the input length.** `recovered=393216`
in every case, whether 1 bit or 49152 bits were embedded. `393216 = 128 × 128 × 3 × 8`
— eight bits for every pixel of the entire cover. `encode` writes `bpc` bits per
pixel into the low bits of the pixel value. `decode` masked each pixel and passed
the result to `np.unpackbits`, which expands each `uint8` into eight bits, seven of
them structural zeros followed by the low `bpc` bits at the end. The decoder returns
a different representation from the one the encoder produced.

**2. `all-zeros` passes with 1.0000.** This is the diagnostic case. A stream that is
seven eighths structural zeros compares equal to an all-zeros payload by
construction. A decoder of this shape would pass any all-zeros test regardless of
what the codec did, which is why the falsifier includes it — it distinguishes a
working codec from one that merely returns zeros.

**3. `all-ones` scores exactly 0.1250.** One in eight. Only every eighth position of
the decoded stream can carry a 1, and the alignment is fixed at the end of each
eight-bit group rather than at the start. An 8× dilation with a fixed phase
predicts precisely this value.

**4. `len1` scores 0.0000.** The single embedded bit was 1, and the first decoded
position is a structural zero.

Taken together these are not a metric artifact. `bit_accuracy` is a correct
function; it was faithfully reporting a decoder reading the wrong representation.

## Scope

`LSBSteganography` only. `DCTSteganography`, `GANEncoderDecoder` and
`AdaptiveJNDSteganography` are excluded by design. The published benchmark reports
chance-level accuracy for LSB, GAN_Enc and Adaptive_JND, but the cause was
established only for LSB, and the other two implement different decoders. No repair
is specified for them and none is implied here.

## After this log

The repair is `LSBSteganography.decode` only. `encode` is not modified: it writes
`bpc` bits per pixel correctly, and the property it satisfies is that the bits are
present in the cover. The defect is entirely in the read path.

---

## Post-fix result

Same interpreter, same test file, no change to the test.

```
PASSED: 18 of 18 cases
```

```
  [PASS] random-seed1   : n=5000  embedded=5000  recovered=49152   bit_accuracy=1.0000
  [PASS] random-seed2   : n=5000  embedded=5000  recovered=49152   bit_accuracy=1.0000
  [PASS] random-seed3   : n=5000  embedded=5000  recovered=49152   bit_accuracy=1.0000
  [PASS] random-seed7   : n=5000  embedded=5000  recovered=49152   bit_accuracy=1.0000
  [PASS] random-seed11  : n=5000  embedded=5000  recovered=49152   bit_accuracy=1.0000
  [PASS] len1           : n=1     embedded=1     recovered=49152   bit_accuracy=1.0000
  [PASS] len7           : n=7     embedded=7     recovered=49152   bit_accuracy=1.0000
  [PASS] len9           : n=9     embedded=9     recovered=49152   bit_accuracy=1.0000
  [PASS] len13          : n=13    embedded=13    recovered=49152   bit_accuracy=1.0000
  [PASS] len101         : n=101   embedded=101   recovered=49152   bit_accuracy=1.0000
  [PASS] len999         : n=999   embedded=999   recovered=49152   bit_accuracy=1.0000
  [PASS] len1001        : n=1001  embedded=1001  recovered=49152   bit_accuracy=1.0000
  [PASS] all-zeros      : n=5000  embedded=5000  recovered=49152   bit_accuracy=1.0000
  [PASS] all-ones       : n=5000  embedded=5000  recovered=49152   bit_accuracy=1.0000
  [PASS] alternating    : n=5000  embedded=5000  recovered=49152   bit_accuracy=1.0000
  [PASS] len-equals-cap : n=49152 embedded=49152 recovered=49152   bit_accuracy=1.0000
  [PASS] bpc2-len4000   : n=4000  embedded=4000  recovered=147456  bit_accuracy=1.0000
  [PASS] bpc3-len4000   : n=4000  embedded=4000  recovered=98304   bit_accuracy=1.0000
```

`recovered` is now `bpc * 49152` in every case, matching what `encode` writes,
instead of the previous fixed `393216`.

### The falsifier caught a defect in the repair

The first implementation of `decode` used descending shift order within each
pixel. It passed every `bpc=1` case and failed `bpc2` at 0.6763 and `bpc3` at
0.4815 — 16 of 18.

Those two cases are in the falsifier because `bpc` is a constructor parameter the
class supports and the published configuration never exercises. Had the
falsifier covered only the published `bpc=1` path, the repair would have shipped
with a broken multi-bit mode and a green test.

Corrected to ascending order, which is what `encode`'s `i % bpc` indexing
requires. The comment in `decode` records this.

## Regenerated benchmark

Full `sgn_simulator.py` run after the fix, clean environment, fresh process:

| method | PSNR | SSIM | bpp | bit accuracy | changed by this repair |
|---|---|---|---|---|---|
| LSB | 61.09 | 1.0000 | 0.1017 | **1.0000** | yes, from 0.50 |
| DCT | 50.42 | 0.9996 | 0.0041 | 1.0000 | no |
| GAN_Enc | 40.24 | 0.9961 | 0.0833 | 0.5002 | **no — out of scope** |
| Adaptive_JND | 61.01 | 1.0000 | 0.1017 | 0.5084 | **no — out of scope** |

`GAN_Enc` and `Adaptive_JND` are unchanged and remain at chance. Their cause is
not established, no repair is specified for them, and this repair does not touch
their decoders.

## What is NOT closed by this repair

`figures/metrics.json` is byte-identical before and after. It still contains

```json
{"methods": ["LSB", "DCT", "GAN_Enc", "Adaptive_JND"]}
```

— four strings and no numbers. **No published figure in this repository is
traceable to a committed artifact, and that was true before the repair and is
still true.** It is a separate defect (DEFECT-004, "artifact with no numeric
content") and it is not part of the row-6 property, which is the codec identity.

Consequently the README table still reads `0.50` for LSB. **It has not been
edited.** Replacing that cell with `1.00` by hand would create a published number
with no artifact behind it, which is the defect this whole exercise exists to
remove. The correct sequence is to give the simulator a numeric artifact first,
then regenerate, then reconcile the README from the artifact.
