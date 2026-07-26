# GIFT-64 Pipeline A2: Linear Constraint Boundary

> Completed locally: 2026-07-26
>
> Scope: recover the LC program's matrix semantics, define a versioned GF(2)
> `ConstraintSet`, and establish a bounded equivalence fixture. This checkpoint
> does not independently reimplement the LC derivation or run LC/LNC Stage 2.

## Result

The supplementary LC stage can now be observed through two explicit layers:

```text
gift64-trail-information/v1
  → hash-pinned temporary LC observation
  → source equations with fixed round-constant terms
  → deterministic GF(2) RREF
  → constraint-set/v1 + semantic affine-space hash
```

The unchanged upstream program is copied to a temporary directory. A
source-hash-pinned instrumentation adds machine-readable observations of the
already-computed matrix rows; it does not change the DDT construction,
Gaussian elimination, record loops or LaTeX stdout. Compilation and all output
remain outside the repository and are removed automatically.

The current full fixture produces:

- 32 constraint sets, one for each positional trail;
- 192 source equations and total rank 192;
- rank 6 and nullity 122 for every trail over 128 master-key bits;
- 32 distinct semantic affine spaces;
- deterministic legacy stdout SHA-256
  `b03a368c3128edf7042f57a9609822be968a324e7163f38c933782c779412a13`.

## Evidence boundary

| Artifact | SHA-256 |
|---|---|
| LC `main.cpp` | `42f734a6cc7969a55fca5ad498ae319c2676fe4c6e3178ff633efa6295df7bd2` |
| `TrailInformation.out` | `fe40ca7b81d4c362d45db58c7c4448317d0305bbd149e04abe12bcede8c02335` |
| One-page linear-constraint supplement | `31d4a9a2c88692f27f6a20ebd3f67ae49821e6773e08baca88eaa656e80bea21` |
| Upstream repository revision | `5de31d9153347e56c7c9260c070384bfeb7feb60` |

The supplement visually arranges four trails for each of the eight sets
`S_0` through `S_7`. The bounded automated oracle checks the first positional
trail against the six equations shown in the first panel. This is a
content-based equivalence check, not a recovered producer-run manifest.

## Recovered LC algorithm

For every trail and every adjacent pair among the eight rounds, the legacy
program:

1. constructs affine descriptions of the valid GIFT S-box input/output
   values for the observed differential transition;
2. creates equations for the previous S-box outputs and next S-box inputs;
3. connects them through the GIFT permutation, round-key bits and constants;
4. performs Gaussian elimination with bridge-state columns first;
5. emits only rows in which all 64 bridge-state variables were eliminated.

DDT entries with six solutions are deliberately removed from this LC table.
Those non-affine cases are handled by the separate linearised-nonlinear stage,
so A2 must not label the LC output as a complete exact right-key space.

The legacy matrix has 242 columns:

| Columns | Meaning |
|---|---|
| `0..63` | temporary 64-bit state at the adjacent-round boundary |
| `64..191` | master-key variables `k_0..k_127` |
| `192..240` | seven fixed round-constant slots for each of seven bridges |
| `241` | equation right-hand side |

Although the formatter prints expressions such as `1` and
`c^9_2` on the left, these are fixed cipher terms, not solver variables. The
contract preserves their names and values as provenance, then XORs their
values into `effective_rhs` before affine-space canonicalisation.

## Round semantics

An eight-round trail over `[5, 13)` has seven adjacent-round bridges. The
legacy loop index `0..6` maps to absolute source rounds `5..11`.

For the bundled trails, non-empty LC equations occur at source rounds 5, 7, 9
and 11. Empty bridge rounds remain represented by the source interval rather
than by invented zero equations.

## `constraint-set/v1`

The common contract records:

- `constraint_kind`, currently `LC`, and field `GF(2)`;
- cipher and the versioned 128-bit master-key variable order;
- source trail hash, positional group/trail and round interval;
- derivation method and pinned source hash;
- source equations, source RHS, fixed terms and effective RHS;
- deterministic reduced-row-echelon rows;
- rank, nullity and semantic SHA-256.

The semantic hash includes the cipher, variable-order identity, variable count
and canonical RREF rows. It excludes equation order, chosen Gaussian basis,
source-round annotations and display text. Two different bases therefore
compare equal only when they represent the same affine master-key space.

Inconsistent systems are rejected instead of being assigned a misleading
nullity or semantic hash.

## First bounded equivalence fixture

The first positional trail normalizes to:

```text
round 5:  k_87 xor k_95 = 0
round 7:  k_30 = 1
round 9:  k_68 xor k_88 = 1
round 9:  k_76 = 1
round 9:  k_80 xor k_88 = 0
round 11: k_17 xor k_25 = 0
```

The first round-9 equation is printed by the program with a fixed `1` on the
left and RHS `0`; normalization correctly moves that fixed term into effective
RHS `1`. The six normalized equations agree with the first panel of the
supplementary PDF.

## Implementation and tests

- `src/shared/constraints.py`
- `src/automated_differential_analysis/adapters/gift64_lc_legacy.py`
- `scripts/inspect_gift64_linear_constraints.py`
- `tests/test_constraints.py`
- `tests/test_gift64_lc_legacy.py`

The 57-test repository suite covers:

- semantic equivalence under different GF(2) bases and row order;
- deterministic JSON round trips and derived-field tamper detection;
- fixed-term evaluation and inconsistent-system rejection;
- strict source hashing and instrumentation-point count;
- strict marker columns, positions, bridge rounds and stderr ownership;
- a real temporary compile/run against the immutable LC source;
- the first published six-equation fixture.

## Claims and limitations

A2 proves that this repository can reproduce and normalize the rows computed
by the pinned legacy LC implementation. It does **not** yet prove independently
that:

- the legacy affine-space construction is correct for every GIFT transition;
- its forward Gaussian elimination exposes every intended LC;
- all 32 panels match the supplement equation by equation;
- LC alone describes the final right-key space;
- the positional groups are the original producer `GroupIndex` order.

The temporary observation is exact with respect to the pinned source, while an
independent LC derivation remains a later verification task.

## Next boundary

The next checkpoint should statically recover the
`3.Finding_linearized_nonlinear_constraints` representation before extending
the contract. It should determine whether each LNC can be represented as
another evaluated GF(2) equation or needs explicit auxiliary/nonlinear
provenance. The shared contract should be reused only after that semantic check.
