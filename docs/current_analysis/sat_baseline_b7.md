# SAT Baseline B7: Controlled Thread Comparison

> Completed locally: 2026-07-26
>
> Scope: a bounded, descriptive comparison of the same four-round GIFT-64 SAT
> instance under one versus two CryptoMiniSat threads. This is not a paper
> runtime comparison or a server benchmark.

## Controlled factors

Both configurations use the same pinned `Differential.cpp`, CryptoMiniSat
`5.14.7`, compiler, C++17/O2 build, objective, 30-second limit and independent
GIFT-64 verifier. The temporary source copy changes only:

```cpp
solver.set_num_threads(1);
```

to `solver.set_num_threads(2);` for the alternative configuration. The source
hash and the exact instrumentation point are checked before compilation.

Five repetitions of each configuration run in alternating order. Raw models,
logs, executables and timing output are not tracked.

## Result on this machine

The observed host has 10 logical CPUs and 16 GiB RAM, running macOS 15.5.

| Threads | Repetitions | Observed median solve wall time | Verified result |
|---:|---:|---:|---|
| 1 | 5 | about 145 ms | SAT, weights 11 / 1 |
| 2 | 5 | about 130 ms | SAT, weights 11 / 1 |

The observed median ratio is about `1.12`: two threads were about 12% faster
on this small local instance. Individual runs include operating-system
scheduling outliers. This does not establish a general scaling result: the
legacy code has no explicit solver-seed API, the instance is very small, and
the comparison is not statistically powered.

## Acceptance criteria

Every repetition was required to have:

- definitive `SAT`;
- independent verification `passed`;
- exact-label eligibility;
- satisfied bound;
- the same objective components: integral weight 11 and decimal count 1.

All ten observations met those conditions. B6 also still passes unchanged.

## Implementation

- `src/automated_differential_analysis/adapters/gift64_improved_legacy.py`:
  hash-pinned optional temporary thread override;
- `scripts/run_gift64_b7.py`: alternating-order 1-thread versus 2-thread run;
- `tests/test_gift64_legacy_adapter.py`: validates the pinned thread override.

Run:

```sh
PYTHONPATH=src python3 scripts/run_gift64_b7.py --repetitions 5
```

## Limit

B7 closes the minimal baseline comparison requirement, but not performance
evaluation. A server comparison needs a fixed host specification, explicit
seed control, a larger instance suite and repeated isolated jobs.
