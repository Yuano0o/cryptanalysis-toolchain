# GIFT-64 Pipeline A3: Linearised Constraint Boundary

> Completed locally: 2026-07-26
>
> Scope: recover the LNC-stage matrix semantics, normalize its combined
> LC-plus-linearised-relation output, and compare that affine space exactly
> against the A2 LC base. This checkpoint does not independently reimplement
> the linearisation algorithm or run fixed-key Stage 2.

## Result

The supplementary LNC stage can now be observed through a hash-pinned,
read-only boundary:

```text
A1 gift64-trail-information/v1
  ├─> A2 LC constraint-set/v1, rank 6
  └─> pinned global LNC-stage observation
        -> LC_PLUS_LINEARIZED_RELATIONS constraint-set/v1, rank 8
        -> constraint-space-comparison/v1
        -> LC implication passes, incremental rank 2
```

The bundled fixture produces:

- 32 combined constraint sets, one for each positional trail;
- 256 source equations, eight per trail;
- combined rank 8 and nullity 120 for every trail;
- 32 distinct combined semantic affine spaces;
- exact implication of every corresponding rank-6 A2 LC space;
- incremental rank 2 for every trail;
- deterministic legacy stdout SHA-256
  `101e0f2918d167a7e3fdc38cdc3c622d0841b9217e0f58622260982bcb42fa2f`.

The unchanged upstream program is copied to a temporary directory. Pinned
instrumentation observes the already-computed final matrix rows on stderr; it
does not change the DDT enumeration, affine-map search, global system,
Gaussian elimination or legacy stdout.

## Evidence boundary

| Artifact | SHA-256 |
|---|---|
| LNC `main.cpp` | `af9f7070e0c46e156ad168e2ae11b090679e74d034bf05ddfbb035800b732f60` |
| LC `main.cpp` | `42f734a6cc7969a55fca5ad498ae319c2676fe4c6e3178ff633efa6295df7bd2` |
| `TrailInformation.out` | `fe40ca7b81d4c362d45db58c7c4448317d0305bbd149e04abe12bcede8c02335` |
| Upstream repository revision | `5de31d9153347e56c7c9260c070384bfeb7feb60` |

All compilation and generated output remain in temporary directories and are
removed automatically.

## Recovered matrix semantics

The legacy LNC program constructs a `761 x 761` GF(2) matrix:

| Columns | Meaning |
|---|---|
| `0..575` | nine 64-bit state layers across the eight-round trail |
| `576..703` | master-key variables `k_0..k_127` |
| `704..759` | eight groups of seven fixed round-constant slots |
| `760` | equation right-hand side |

The first 576 columns are elimination variables. A row is printed only when
all of those state columns have been eliminated.

Unlike A2, which eliminates one adjacent-round bridge at a time, the LNC
program builds one global system across the full half-open interval `[5, 13)`.
The normalized equations therefore use round 5 only as a provenance anchor;
their true derivation scope is the set-level source interval and global
derivation method.

## Meaning of the linearisation

For affine DDT transitions, the program adds input-affine equations. It also
uses `DDTInOutRelation`, an affine input-to-output map recovered by exhaustive
enumeration of valid S-box value pairs.

The final system remains an affine GF(2) system over intermediate state bits,
master-key bits and fixed constants. It does not introduce persistent
nonlinear monomial variables. Consequently, the A2 `GF2Equation`,
fixed-term evaluation and canonical RREF machinery can be reused.

This reuse describes the representation only. It is not yet an independent
proof that the legacy program constructs every intended linearised relation
correctly.

## Why the output is not eight new LNC equations

The LNC-stage program includes both:

1. affine input constraints that carry the existing LC information; and
2. additional linearised input/output relations.

It then eliminates the global state variables and prints a new basis of the
combined master-key space. Several printed rows may equal A2 rows, while other
rows may be different linear combinations of the A2 basis.

The stable new information is therefore not a particular selection of two
printed equations. The stable result is:

```text
rank(combined) - rank(LC) = 8 - 6 = 2
```

after proving algebraically that the combined system implies the LC system.
A complementary equation basis is not unique and is deliberately not treated
as canonical.

## Structured artifacts

### Combined `ConstraintSet`

Each post-elimination LNC-stage space is stored with:

- constraint kind `LC_PLUS_LINEARIZED_RELATIONS`;
- the same GIFT-64 128-bit master-key variable order as A2;
- source trail hash and positional group/trail;
- global round interval `[5, 13)`;
- fixed round-constant provenance and evaluated effective RHS values;
- canonical RREF rows, rank, nullity and semantic SHA-256;
- pinned LNC source hash and derivation method.

### `constraint-space-comparison/v1`

Each comparison records:

- source artifact hash and positional group/trail;
- A2 LC and A3 combined constraint-set identifiers;
- both semantic hashes and ranks;
- whether the combined system implies the LC system;
- incremental rank only when implication holds.

The implication check appends the LC equations to the combined affine system
and verifies that canonical rank does not increase. A contradictory or
independent LC equation therefore fails the check rather than producing a
misleading incremental rank.

## First bounded fixture

For the first positional trail, the legacy LNC-stage output normalizes to an
eight-dimensional combined space. Its source rows include:

```text
k_4 xor k_12 xor k_38 xor k_40 xor k_68 xor k_95
    xor k_121 xor k_123 = 0
k_12 xor k_30 xor k_88 xor k_122 xor k_123 = 0
k_17 xor k_25 = 0
k_30 = 1
k_68 xor k_80 = 1
k_76 = 1
k_80 xor k_88 = 0
k_87 xor k_95 = 0
```

The first trail's combined space implies all six A2 LC equations and adds
exactly two independent restrictions.

## Implementation and tests

- `src/shared/constraints.py`
- `src/automated_differential_analysis/adapters/gift64_lnc_legacy.py`
- `scripts/inspect_gift64_linearized_constraints.py`
- `tests/test_constraints.py`
- `tests/test_gift64_lnc_legacy.py`

Coverage includes:

- affine-space implication under different bases;
- non-implication and incompatible-metadata cases;
- versioned incremental-rank comparison artifacts;
- strict LNC source hashing and instrumentation ownership;
- key-column and fixed-term mapping;
- malformed stderr and record-position rejection;
- a real temporary LC and LNC compile/run over all 32 trails;
- first-trail equation content;
- full-corpus rank, implication, semantic-space and stdout-hash regression.

## Claims and limitations

A3 proves that this repository can reproduce, normalize and algebraically
compare the master-key affine spaces emitted by the pinned LC and LNC-stage
programs.

It does **not** yet prove independently that:

- the legacy `DDTInOutRelation` construction is correct for every transition;
- the global Gaussian elimination exposes every intended relation;
- the resulting affine space equals the complete exact right-key space;
- Stage 2 finds no further fixed-key restrictions;
- the supplied trail positions match the producer's `GroupIndex` order;
- the paper-level differential result has been reproduced.

## Next boundary

The next demo checkpoint should define a deterministic
`generated-for-demo` 128-bit key-corpus contract and wrap the Stage 2
fixed-key SAT program with:

- configurable sample size;
- explicit trail selection;
- strict key-corpus validation;
- controlled solver statuses and limits;
- structured summary and provenance;
- a small bounded end-to-end regression.
