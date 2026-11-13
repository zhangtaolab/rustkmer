# N-read Semantics

How non-ACGT bases (N, n, and any other byte) affect k-mer counts in RustKmer,
and what changed for Python users in Phase 9.

## What skip-N means

RustKmer counts every length-k window of a sequence **unless the window
contains a byte outside `A`, `C`, `G`, and `T`**. A window containing an `N`,
a lowercase `n`, or any other non-ACGT byte is skipped: it is never counted,
and it never contributes to `total_kmers` or to any k-mer's count.

- Each window is evaluated independently against the raw bytes. A skipped
  window does not truncate the sequence; later windows are still counted.
- Windows never span record boundaries. Each FASTA/FASTQ record is counted on
  its own; the end of one record and the start of the next are never joined
  into a k-mer.

## The D2 change: Python now matches the CLI

The CLI has always used skip-N semantics. Before Phase 9, the Python surface
behaved differently: `PyCounter.add_sequence`, `add_from_fasta`, and
`add_from_fastq` stripped non-ACGT bases and joined the remaining flanks,
which created chimeric k-mers that do not occur in the input. Phase 9 (D2)
removed that pre-filter. All Python counting inputs now skip non-ACGT windows
exactly like the CLI, through the same shared window extractor and parser.

## Measured evidence

The `n_read_differential.py` harness runs nine deterministic FASTQ cases at
k=21 through both surfaces on identical bytes (`canonical=True`,
`threads=1`). The committed pre-D2 artifact and the post-D2 re-run give these
distinct / total counts:

| Case | CLI | Python pre-D2 | Python post-D2 |
|------|-----|---------------|----------------|
| `control_no_n` | 2 / 10 | 2 / 10 | 2 / 10 |
| `n_at_first` | 2 / 9 | 2 / 9 | 2 / 9 |
| `n_at_window_end` | 0 / 0 | 9 / 9 | 0 / 0 |
| `n_at_window_start` | 1 / 1 | 9 / 9 | 1 / 1 |
| `n_at_last` | 2 / 9 | 2 / 9 | 2 / 9 |
| `multiple_n` | 0 / 0 | 7 / 7 | 0 / 0 |
| `lowercase_n` | 0 / 0 | 9 / 9 | 0 / 0 |
| `record_boundary` | 2 / 8 | 2 / 8 | 2 / 8 |
| `short_read` | 0 / 0 | 0 / 0 | 0 / 0 |
| **Nine-case total** | **37** | **70** | **37** |

In total, 33 chimeric k-mers are eliminated. The four affected cases
(`n_at_window_end`, `n_at_window_start`, `multiple_n`, `lowercase_n`) were
the only ones where Python's strip-and-join behavior produced keys the CLI
never counted. After D2 every cell is equal across surfaces: 0 Python-only
keys, 0 CLI-only keys, and 0 shared-key count deltas. The N-free control is
unchanged at 2 distinct / 10 total.

## Why total_kmers drops

`total_kmers` is the sum of every counted window. Because a window containing
a non-ACGT byte is now skipped instead of being rebuilt from its flanks,
`total_kmers` is smaller for N-containing input: the Python nine-case total
falls from 70 to 37, matching the CLI's 37.

This is by design, not data loss. The dropped k-mers were never present in
the input — they were artifacts of joining bases across a skipped position.
Reverting to strip-and-join to restore the old total would re-introduce those
chimeric k-mers; the old total is not preserved by adding flank-joined
windows back.

## Whitespace and other non-ACGT bytes

The same rule covers every non-ACGT byte, including whitespace. In
`add_sequence`, a sequence containing spaces, tabs, newlines, or any other
character outside `A`, `C`, `G`, and `T` has every overlapping window
skipped. For example, at k=7:

```python
import pyrustkmer

counter = pyrustkmer.PyCounter(7)
counter.add_sequence("ACG TACG ACGT")   # every 7-mer spans a space
print(counter.get_stats().total_kmers)  # 0
```

Before Phase 9 the spaces were stripped and the flanks joined, producing
k-mers that do not occur in the input. Newlines and other whitespace are
treated the same way: they break windows, and there is no strip-and-join
step left to hide them.

## Strict FASTA/FASTQ parsing

`add_from_fasta` and `add_from_fastq` now parse through the same strict
readers as the CLI, replacing the old lenient line loop. Malformed input
raises `ValueError` with the parse context instead of being silently
misparsed:

```python
import pyrustkmer

counter = pyrustkmer.PyCounter(21)
try:
    counter.add_from_fastq("truncated.fastq")
except ValueError as exc:
    print(f"invalid FASTQ: {exc}")
```

## No new API

There is no new method and no Python-visible skipped-window counter. To see
how many windows were skipped, compare `total_kmers` and the per-k-mer count
map against the input: skipped windows simply do not appear. The `PyCounter`
counting methods keep their existing signatures.

## See also

- [Counting k-mers](counting-kmers.md)
- [Error Recovery and Graceful Degradation](error-recovery.md)
