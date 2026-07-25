# SAT Baseline Static Map

> Baseline:
> `../upstream/_archives/Improved_Attacks_GIFT64-main.zip::Improved_Attacks_GIFT64-main/Differential.cpp`
>
> Archive SHA-256:
> `0c08cc325e1e857e5e5a0015e1d5e30cd550aaf19ef8a6b10e9d19596008f52d`
>
> Member SHA-256:
> `92b12fd9c65f5870c8f43b0b2e824c4afe789436290cc22e49d238362440c25c`

## Fixed configuration

| Setting | Value |
|---|---|
| Rounds | 4 |
| State size | 64 bits |
| Parallel S-boxes | 16 per round |
| Integral weight bound | `sum(p,q,m) <= 11` |
| Decimal indicator bound | `sum(w) <= 1` |
| Solver threads | 1 |
| Solver calls | 1 |
| Nonzero restriction | At least one bit in `xin[0]` is active |

The two bounds are separate. The source does not encode a single floating-point
inequality.

## Primary variable allocation

For each round `r = 0..3`, the source allocates variables in this order:

| Array | Count per round | Meaning |
|---|---:|---|
| `xin[r]` | 64 | Input difference bits before the S-box layer |
| `p[r]` | 16 | First integer-weight indicator per S-box |
| `q[r]` | 16 | Second integer-weight indicator per S-box |
| `m[r]` | 16 | Third integer-weight indicator per S-box |
| `w[r]` | 16 | `0.415` decimal-weight indicator per S-box |

This yields `4 x 128 = 512` allocated variables.

For rounds 0-2, `xout[r][i]` aliases `xin[r+1][i]`; no new variables are
created. The final `xout[3]` allocates 64 additional variables.

Primary-variable subtotal: `512 + 64 = 576`.

## Sequential-counter variables

### Integral component

- input indicators: `16 x 4 x 3 = 192`;
- bound: 11;
- auxiliary array: `(192 - 1) x 11 = 2101` variables.

### Decimal component

- input indicators: `16 x 4 = 64`;
- bound: 1;
- auxiliary array: `(64 - 1) x 1 = 63` variables.

### Total variables

```text
576 primary
+ 2101 integral-counter
+   63 decimal-counter
= 2740 variables
```

This is the expected `solver.new_vars` value for the fixed source.

## Expected clause count

| Component | Clauses |
|---|---:|
| Nonzero input | 1 |
| S-box restrictions: `4 x 16 x 55` | 3520 |
| Sequential counter for `192 <= 11` | 4382 |
| Sequential counter for `64 <= 1` | 188 |
| Total | 8091 |

The count is derived statically from the fixed source. It should be checked
against the controlled adapter before accepting the first solve.

## S-box restriction semantics

Each S-box uses a 12-variable tuple:

```text
X[0:4]   = input-difference nibble bits
X[4:8]   = output-difference nibble bits after undoing/aligning permutation
X[8]     = p
X[9]     = q
X[10]    = m
X[11]    = w
```

The 55 rows are forbidden partial assignments:

- row value `0`: assignment bit is zero;
- row value `1`: assignment bit is one;
- row value `5`: don't care;
- the emitted clause negates the represented partial assignment.

A complete static truth-table check against the GIFT S-box DDT produced:

- 55 restriction rows;
- 157 impossible DDT cells rejected;
- 78 cells with count 2 accepted at integral weight 3;
- 18 cells with count 4 accepted at integral weight 2;
- 2 cells with count 6 accepted at weight `1 + 0.415`;
- the zero-to-zero cell accepted at weight 0;
- zero semantic mismatches between accepted assignments and the DDT/weight
  interpretation.

For the two count-6 transitions, the source may use different one-hot positions
among `p/q/m`. The positions are not semantically distinct because the objective
uses only `p + q + m`; the semantic weight is still `1 + 0.415`.

The future verifier must therefore validate the summed integral component and
`w`, not require one canonical bit pattern for `p/q/m`.

## Permutation direction

The source defines the standard GIFT-64 permutation `P` and assigns:

```text
y[i] = xout[r][P[i]]
```

The S-box output-difference bit at logical position `i` is therefore constrained
against state bit `xout[r][P[i]]`, matching:

```text
b[P(i)] <- b[i]
```

The independent verifier should:

1. evaluate each S-box transition from `xin[r]` to logical S-box output `y`;
2. apply `P` to produce `xout[r]`;
3. compare `xout[r]` with `xin[r+1]` for rounds 0-2.

This avoids silently reversing the permutation in the verifier.

## Model output contract

On `SAT`, the source prints four blocks:

```text
Round: <r>
xin:
<16 hexadecimal nibbles grouped 4 + 4 + 4 + 4>
xout:
<16 hexadecimal nibbles grouped 4 + 4 + 4 + 4>
```

Nibble construction is:

```text
bit[4*sbox + 0] -> nibble bit 3 (MSB)
bit[4*sbox + 1] -> nibble bit 2
bit[4*sbox + 2] -> nibble bit 1
bit[4*sbox + 3] -> nibble bit 0 (LSB)
```

The source prints nothing for `UNSAT` or `UNKNOWN`, and always returns process
exit code 0. A controlled adapter must not use empty stdout as the solver
status; it must obtain and record `lbool ret` explicitly.

## Static risks to preserve in the controlled baseline

- no CLI or configuration input;
- no explicit `UNSAT`/`UNKNOWN` output;
- no runtime, variable or clause summary;
- no model validation;
- no canonical result artifact;
- no proof or independent checker;
- `p/q/m` one-hot position is not a semantic identity;
- the paper-scale 12/13-round enumerations are not present.

## B1 result

Checkpoint B1 is complete:

- archive/member identity recorded;
- fixed configuration recorded;
- primary and auxiliary variables counted;
- clause count derived;
- S-box restriction table checked against the GIFT DDT;
- weight semantics checked;
- permutation direction and stdout decoding mapped.

Next checkpoint: B2, versioned research-side configuration and
`SolverRequest`/`SolverResult` contracts.
