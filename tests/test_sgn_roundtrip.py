"""
Round-trip falsifier for LSBSteganography.

SPECIFICATION (frozen 2026-09-30, before any change to this repository):

    The property is that `decode(encode(payload))` reproduces the payload
    exactly, for any payload and any cover. This is a mathematical identity,
    not a quality metric. It does not depend on the aggregate `bit_accuracy`
    figure, on the README table, or on any claim in the paper.

    A repair of the codec is accepted when this file passes. It is not
    accepted when `bit_accuracy` happens to rise.

SCOPE: LSBSteganography only.

    DCTSteganography, GANEncoderDecoder and AdaptiveJNDSteganography are
    deliberately excluded. The published benchmark reports chance-level bit
    accuracy for LSB, GAN_Enc and Adaptive_JND, but the cause was established
    only for LSB. The other three have their own decode implementations and the
    mechanism proven for LSB is not assumed to apply to them. Extending these
    tests to them is a separate exercise requiring its own evidence.

This file is a pre-fix falsifier. It was executed against the frozen code
before the repair existed, and it failed. See FALSIFIER-LOG.md.
"""

import sys
import os

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sgn_simulator import (  # noqa: E402
    ImageGenerator,
    LSBSteganography,
    generate_secret_message,
    bit_accuracy,
    IMG_SIZE,
)


def roundtrip(payload, cover, bpc=1):
    """Run the codec and return the bits recovered from the first len(payload)."""
    method = LSBSteganography(bits_per_channel=bpc)
    stego, n_bits = method.encode(cover, payload)
    recovered = method.decode(stego)
    return recovered, n_bits


def check(name, payload, cover, bpc=1):
    """Assert the exact round-trip identity. Returns (ok, detail)."""
    recovered, n_bits = roundtrip(payload, cover, bpc)
    n = min(n_bits, len(payload), len(recovered))
    exact = bool(np.array_equal(recovered[:n], payload[:n]))
    acc = float(np.mean(recovered[:n] == payload[:n])) if n else 0.0
    return exact, f"{name}: n={n} embedded={n_bits} recovered={len(recovered)} bit_accuracy={acc:.4f}"


def main():
    generator = ImageGenerator()
    cover = generator.generate("natural_like")

    cases = []

    # 1. Random payloads, several seeds. Covers the general case.
    for seed in (1, 2, 3, 7, 11):
        payload = np.random.default_rng(seed).integers(0, 2, 5000).astype(np.uint8)
        cases.append((f"random-seed{seed}", payload))

    # 2. Lengths that are not multiples of 8. A decoder that dilates its
    #    output by a factor of 8 passes only for some lengths by accident.
    for length in (1, 7, 9, 13, 101, 999, 1001):
        payload = np.random.default_rng(1000 + length).integers(
            0, 2, length
        ).astype(np.uint8)
        cases.append((f"len{length}", payload))

    # 3. Degenerate payloads. A constant payload exposes any decoder that
    #    returns a fixed structural value rather than reading the cover.
    cases.append(("all-zeros", np.zeros(5000, dtype=np.uint8)))
    cases.append(("all-ones", np.ones(5000, dtype=np.uint8)))
    alternating = np.tile(np.array([0, 1], dtype=np.uint8), 2500)
    cases.append(("alternating-0101", alternating))

    # 4. Capacity edge: a payload exactly filling the cover.
    capacity = IMG_SIZE * IMG_SIZE * 3
    cases.append((
        "len-equals-capacity",
        np.random.default_rng(4242).integers(0, 2, capacity).astype(np.uint8),
    ))

    # 5. Bits per channel above 1, which the class supports and the
    #    published configuration does not exercise.
    for bpc in (2, 3):
        payload = np.random.default_rng(500 + bpc).integers(
            0, 2, 4000
        ).astype(np.uint8)
        cases.append((f"bpc{bpc}-len4000", payload))

    failures = []
    print("=" * 78)
    print("ROUND-TRIP FALSIFIER — LSBSteganography")
    print("property: decode(encode(payload)) == payload, exactly")
    print("=" * 78)

    for name, payload in cases:
        bpc = 3 if name.startswith("bpc2") else (2 if name.startswith("bpc3") else 1)
        exact, detail = check(name, payload, cover, bpc)
        status = "PASS" if exact else "FAIL"
        print(f"  [{status}] {detail}")
        if not exact:
            failures.append(name)

    print("-" * 78)
    if failures:
        print(f"FAILED: {len(failures)} of {len(cases)} cases")
        print("failing:", ", ".join(failures))
        return 1

    print(f"PASSED: {len(cases)} of {len(cases)} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
