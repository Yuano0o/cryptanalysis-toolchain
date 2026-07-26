# GIFT-64 Pipeline A1: `TrailInformation.out`

> Completed: 2026-07-26
>
> Scope: recover and test the first immutable artifact boundary in the
> supplementary differential-level pipeline. This checkpoint does not run the
> trail search, LC/LNC extraction, fixed-key tests or probability experiments.

## Result

The four bundled `TrailInformation.out` files are byte-identical and can be
read through the strict versioned contract
`gift64-trail-information/v1`.

The parser is:

- read-only with respect to `../upstream/`;
- strict about the exact record, line and word counts;
- explicit about file position versus semantic identifiers;
- deterministic and independently tested with a small handwritten fixture;
- pinned to the bundled source hash when used by the inspection script.

This establishes the first concrete boundary of the differential-level
pipeline:

```text
legacy trail search / undocumented selection
  → TrailInformation.out
  → strict parser
  → normalized trail corpus
  → LC/LNC extraction (next checkpoint)
```

It does not establish how the 32 bundled trails were selected from all solver
solutions or how the eight single-group runs were assembled.

## Producer and consumers

| Role | Upstream program | Relevant behavior |
|---|---|---|
| Producer | `1.Searching_for_trails_contained_in_a_differential/main.cpp` | Selects one `GroupIndex`, enumerates solver models and writes `TrailInformation.out` |
| Consumer | `2.Finding_linear_constraints/main.cpp` | Reads eight positional groups with four trails per group |
| Consumer | `3.Finding_linearized_nonlinear_constraints/main.cpp` | Reads the same corpus for LNC extraction |
| Consumer | `4.Stage2_test/main.cpp` | Reads 32 records, but its current test loop evaluates only trail position 0 |
| Consumer | `5.Stage3_test/main.cpp` | Reads 32 records and evaluates the configured `TestTrailIndex` |

The producer defaults are `ObjectiveProb=50`, `trailround=8` and
`GroupIndex=0`. Its output label says `Master Key`, but the downstream
key-state reconstruction shows that the eight words are a **key-state
difference at round 4**, not a secret master-key value. The normalized field is
therefore named `key_state_difference_words`.

## Recovered physical format

The canonical corpus has:

- SHA-256
  `fe40ca7b81d4c362d45db58c7c4448317d0305bbd149e04abe12bcede8c02335`;
- 12,063 bytes, 2,304 hexadecimal words and 544 logical lines;
- no final newline;
- 32 positional records: eight groups times four trails;
- 72 words and 17 logical lines per record.

One record is:

```text
8 × 16-bit words: key-state difference at absolute round 4
for absolute rounds 5 through 12:
  4 × 16-bit words: round input difference
  4 × 16-bit words: round output difference
```

Words are four-digit hexadecimal tokens. Each four-word state is 64 bits; each
eight-word key state is 128 bits. Within a word, both the producer and
consumers expand bits from bit 15 to bit 0. The normalized state consequently
uses word order as written and MSB-first nibble/bit expansion.

The round interval is half-open `[5, 13)`. The key-state anchor at round 4 is
confirmed by the Stage 2 and Stage 3 use of
`RoundKeyFullStateIndex[StartingRound - 1]`.

## Positional groups are not producer group identifiers

The file's eighth key-state word by group position is:

```text
000a, 0005, 00a0, 0050, 0a00, 0500, a000, 5000
```

The producer's `KeyDiff8Group` declaration order is:

```text
000a, a000, 0500, 0a00, 0005, 0050, 00a0, 5000
```

Therefore `group_position` is a reliable property of this file, but it must
not be silently interpreted as the producer's `GroupIndex`. The current
materials contain no manifest connecting the concatenated file positions to
the individual producer runs.

## Contract and validation

Implementation:

- `src/automated_differential_analysis/formats/gift64_trail_information.py`
- `scripts/inspect_gift64_trail_information.py`
- `tests/test_gift64_trail_information.py`

The parser checks:

1. ASCII input and optional exact source SHA-256;
2. no blank records and the exact logical-line count;
3. four-digit hexadecimal words and exact words per line;
4. 32 records under the default layout;
5. eight rounds per trail with absolute rounds 5 through 12;
6. `output_state[r] == input_state[r+1]`;
7. a nonzero first-round input difference;
8. a common key-state difference within each positional group;
9. distinct key-state differences across the eight groups.

The compact inspection output contains only counts, layout, validation status
and source hash. Raw trails are neither copied nor committed.

## Test evidence

The repository suite now has 47 passing tests, including:

- a handwritten one-trail, two-round fixture;
- bit, nibble, word and absolute-round semantics;
- missing-final-newline and trailing-space compatibility;
- negative cases for continuity, token width, line count and hash;
- integration checks for all four immutable upstream copies.

## What remains unknown

The following facts cannot be recovered from the bundled file alone:

- the command/configuration and random seed for every producer run;
- why exactly four trails were retained for each key-difference group;
- how the eight single-group outputs were selected, ordered and concatenated;
- a stable identifier connecting file position, producer `GroupIndex` and the
  paper's reported cases;
- whether the file is complete or a hand-selected intermediate artifact.

These are provenance gaps, not parser errors. They block an exact reproduction
of trail generation/selection, but do not block deterministic LC/LNC parsing
against the supplied fixture.

## Next boundary

Checkpoint A2 should recover the LC output semantics and define a versioned
`ConstraintSet` contract. It should use the normalized corpus as its only trail
input and compare the new representation against the legacy LC program on a
small bounded fixture. Related-key DDT verification should be added separately:
the existing B3 verifier models single-key round continuity and must not be
misapplied to these related-key trails.
