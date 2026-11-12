#!/usr/bin/env python3
"""Select a deterministic uniform random-record subslice from gzipped FASTQ.

Algorithm R performs one streaming pass with memory bounded by the requested
record count. Selected records are emitted in ascending source-index order,
with a manifest that makes the selection and output bytes reproducible.
Stdlib only.
"""

import argparse
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    # Direct script execution needs the checkout root for the scripts package.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import fingerprint, validate_path


def reservoir_slice(gz_path, n_reads, seed, out_path, manifest_path):
    """Write a seeded random-record FASTQ slice and its selection manifest.

    Args:
        gz_path: Gzipped FASTQ source, streamed through ``gunzip -c``.
        n_reads: Positive number of complete four-line records to select.
        seed: Integer seed for the isolated Algorithm R random generator.
        out_path: Destination FASTQ path, written in source-index order.
        manifest_path: Destination JSON selection manifest.

    Returns:
        The manifest dictionary, including source fingerprint and indices.

    Raises:
        ValueError: If arguments, paths, or FASTQ record framing are invalid.
        RuntimeError: If decompression fails or the source has no records.
        OSError: If a required file cannot be read or written.
    """
    if isinstance(n_reads, bool) or not isinstance(n_reads, int) or n_reads < 1:
        raise ValueError(f"n_reads must be a positive integer, got {n_reads!r}")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(f"seed must be an integer, got {seed!r}")

    source = Path(validate_path(gz_path))
    if not source.is_file():
        raise ValueError(f"input not found or not a file: {source}")
    source_fingerprint = fingerprint(source)

    # Seed BEFORE any selection — the determinism contract. Algorithm R keeps
    # exactly n_reads records, never the full source, in memory.
    rng = random.Random(seed)
    reservoir = []
    source_record_count = 0
    stream_exhausted = False
    proc = subprocess.Popen(
        ["gunzip", "-c", str(source)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        while True:
            record = [proc.stdout.readline() for _ in range(4)]
            if record[0] == b"":
                stream_exhausted = True
                break
            if any(line == b"" for line in record):
                raise ValueError(
                    f"malformed FASTQ {source}: line count is not a multiple of 4"
                )

            source_index = source_record_count
            source_record_count += 1
            if source_index < n_reads:
                reservoir.append((source_index, record))
            else:
                replacement = rng.randrange(source_index + 1)
                if replacement < n_reads:
                    reservoir[replacement] = (source_index, record)
    finally:
        proc.stdout.close()
        if not stream_exhausted and proc.poll() is None:
            proc.terminate()
        returncode = proc.wait()
        decompressor_error = proc.stderr.read().decode(
            "utf-8", errors="replace"
        ).strip()
        proc.stderr.close()

    if source_record_count == 0:
        detail = f": {decompressor_error}" if decompressor_error else ""
        raise RuntimeError(
            f"slice of {source} produced 0 lines — empty or invalid gz input"
            f"{detail}"
        )
    if returncode != 0:
        detail = f": {decompressor_error}" if decompressor_error else ""
        raise RuntimeError(f"gunzip failed rc={returncode} on {source}{detail}")
    if source_record_count < n_reads:
        raise ValueError(
            f"requested {n_reads} reads but {source} contains only "
            f"{source_record_count} records; refusing to truncate"
        )

    selected = sorted(reservoir, key=lambda item: item[0])
    output_hash = hashlib.sha256()
    with open(out_path, "wb") as out:
        for _, record in selected:
            for line in record:
                out.write(line)
                output_hash.update(line)

    manifest = {
        "source": source_fingerprint,
        "seed": seed,
        "requested_reads": n_reads,
        "selected_reads": len(selected),
        "selected_indices": [index for index, _ in selected],
        "output_sha256": output_hash.hexdigest(),
        "record_lines": 4,
    }
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return manifest


def main(argv=None):
    """Run the random-record slicer CLI; invalid inputs always exit 2."""
    parser = argparse.ArgumentParser(
        description="Select a seeded uniform random-record gzipped FASTQ slice."
    )
    parser.add_argument("--input", required=True, help="source .fq.gz path")
    parser.add_argument("--reads", type=int, required=True,
                        help="number of records to select (must be > 0)")
    parser.add_argument("--seed", type=int, default=42,
                        help="RNG seed (default: 42)")
    parser.add_argument("--out", required=True, help="output FASTQ path")
    parser.add_argument("--manifest", required=True,
                        help="output selection-manifest JSON path")
    args = parser.parse_args(argv)
    if args.reads < 1:
        parser.error(f"--reads must be >= 1, got {args.reads}")

    try:
        manifest = reservoir_slice(
            args.input, args.reads, args.seed, args.out, args.manifest
        )
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")

    print(
        f"wrote {manifest['selected_reads']} randomly selected reads "
        f"(seed {manifest['seed']}) to {args.out}"
    )


if __name__ == "__main__":
    main()
