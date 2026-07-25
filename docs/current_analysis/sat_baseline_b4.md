# SAT Baseline B4: CryptoMiniSat Compile and Smoke Solve

> Completed: 2026-07-26
>
> Scope: local solver installation, out-of-tree compilation and one short
> legacy smoke solve. No upstream file was modified and no generated output was
> added to Git.

## Outcome

The archived four-round GIFT-64 program compiles and runs on the current
Apple-silicon environment with:

| Component | Observed value |
|---|---|
| CryptoMiniSat | `5.14.7` |
| CryptoMiniSat installation | Homebrew bottle |
| Required library dependency | GMP `6.3.0` |
| Compiler | Apple clang `14.0.3` |
| Target | `arm64-apple-darwin24.5.0` |
| C++ language level | C++17 |
| Solver threads in source | `1` |
| Upstream source SHA-256 | `92b12fd9c65f5870c8f43b0b2e824c4afe789436290cc22e49d238362440c25c` |

The installed CryptoMiniSat headers require C++17. An initial C++11 compile
therefore failed in the library headers; changing only the compiler language
level to C++17 was sufficient. The upstream source remained unchanged.

## Reproduction boundary

The compile was performed in a temporary directory using the CryptoMiniSat and
GMP include/library prefixes reported by Homebrew. In portable form, the
command is:

```sh
CMS_PREFIX="$(brew --prefix cryptominisat)"
GMP_PREFIX="$(brew --prefix gmp)"
BUILD_DIR="$(mktemp -d /tmp/gift64-b4.XXXXXX)"

clang++ -std=c++17 -O2 \
  -I"${CMS_PREFIX}/include" \
  -I"${GMP_PREFIX}/include" \
  ../upstream/Improved_Attacks_GIFT64/Differential.cpp \
  -L"${CMS_PREFIX}/lib" \
  -L"${GMP_PREFIX}/lib" \
  -Wl,-rpath,"${CMS_PREFIX}/lib" \
  -Wl,-rpath,"${GMP_PREFIX}/lib" \
  -lcryptominisat5 -lgmpxx -lgmp \
  -o "${BUILD_DIR}/gift64_differential"
```

The resulting executable is an ARM64 Mach-O linked to CryptoMiniSat 5.14 and
GMP. The linker emitted deployment-target warnings because the Homebrew bottles
were built for a newer macOS target than the compiler's default target; the
binary nevertheless linked and ran successfully.

## Smoke observation

One invocation:

- returned process exit code `0`;
- printed exactly four sequential round blocks;
- printed one 16-nibble `xin` and one 16-nibble `xout` state per round;
- completed in approximately `0.19 s` wall time in this single observation.

The raw stdout, executable and build directory are not tracked. The measured
time is not a benchmark: it is one warm-state local smoke observation with no
controlled repetition, resource accounting or comparable historical
environment.

## What B4 does and does not prove

The source prints round states only inside `if (ret == l_True)`, so the observed
model-shaped output is evidence that this invocation reached CryptoMiniSat's
SAT branch.

However, the legacy program:

- always returns process exit code `0`;
- prints no explicit status token;
- emits nothing for both `UNSAT` and `UNKNOWN`;
- does not expose elapsed time, memory, variable/clause counts or a model
  artifact through the shared contracts;
- hard-codes its parameters at compile time.

Therefore B4 establishes only the **legacy compile-and-run boundary**. It does
not yet satisfy the controlled adapter requirement to distinguish `SAT`,
`UNSAT`, `UNKNOWN`, `TIMEOUT` and `ERROR`.

## Next boundary

B5 should add a narrow owned adapter without editing upstream. It should:

1. expose the solver return status explicitly;
2. decode stdout/model data into `TrailRecord`;
3. pass the decoded record through the B3 independent verifier;
4. emit a versioned `SolverResult`;
5. keep raw models, logs and binaries outside Git.
