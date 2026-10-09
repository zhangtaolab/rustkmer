#!/usr/bin/env python3
"""Deterministic synthetic FASTQ generator for the rustkmer benchmark harness.

Byte-identical output for identical arguments: the RNG is explicitly seeded
before any sequence is generated, so every machine produces the same file
(BENCH-04). Stdlib only.
"""

import argparse
import random
import sys

BASES = ("A", "C", "G", "T")


def generate_fastq(reads: int, length: int, out_path: str) -> None:
    """Write `reads` 4-line FASTQ records to `out_path`.

    Headers are sequential (R0000001...), sequences are seeded random ACGT,
    and every quality line is `length` repeated 'I' characters.
    """
    with open(out_path, "w", newline="\n") as fh:
        for i in range(1, reads + 1):
            seq = "".join(random.choices(BASES, k=length))
            fh.write(f"@R{i:07d}\n")
            fh.write(seq + "\n")
            fh.write("+\n")
            fh.write("I" * length + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic synthetic FASTQ file."
    )
    parser.add_argument("--reads", type=int, required=True,
                        help="number of reads to generate (must be > 0)")
    parser.add_argument("--length", type=int, default=150,
                        help="read length in bases (default: 150)")
    parser.add_argument("--seed", type=int, default=42,
                        help="RNG seed (default: 42)")
    parser.add_argument("--out", required=True,
                        help="output FASTQ path")
    args = parser.parse_args()

    if args.reads < 1:
        parser.error(f"--reads must be >= 1, got {args.reads}")
    if args.length < 1:
        parser.error(f"--length must be >= 1, got {args.length}")
    if args.length < 2:
        parser.error("--length must be >= 2 to contain at least one k-mer")

    # Seed BEFORE any sequence generation — the determinism contract.
    random.seed(args.seed)
    generate_fastq(args.reads, args.length, args.out)
    print(f"wrote {args.reads} reads x {args.length} bp (seed {args.seed}) "
          f"to {args.out}")


if __name__ == "__main__":
    main()
