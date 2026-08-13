# Research Source Scan

> Date: 2026-07-25
>
> This report is based on read-only inspection. No upstream code was modified,
> no dependencies were installed, and no experiments were run.

## 1. Scope

### Locally scanned upstream repositories

1. `../upstream/Supplementary_Material_GIFT-64_Differential/`
2. `../upstream/Accelerating_Automatic_Search/`
3. `../upstream/Supplementary_Material_BAKSHEESH/`
4. `../upstream/CRAFT-and-WARP/`

### Additional locally scanned archive

- `../upstream/_archives/Improved_Attacks_GIFT64-main.zip`

### Referenced but not locally available

- `NeuroGIFT-V1`

The `NeuroGIFT-V1` code source is empty/not locally available. It is retained
in the research map because it has a clear conceptual role, but no claims about
its entry points, modules, inputs, outputs, dependencies, or completeness are
made.

### Nine locally available papers

1. *Accelerating the Search of Differential and Linear Characteristics with the
   SAT Method*
2. *A Deeper Look at Related-Key Differentials of GIFT-64 from Trails to
   Differentials*
3. *A Linearisation Method for Identifying Dependencies in Differential
   Characteristics*
4. *More Accurate Differential Properties of LED64 and Midori64*
5. *Investigation of the Optimal Linear Characteristics of BAKSHEESH*
6. *NeuroGIFT: Using a Machine Learning Based SAT Solver for Cryptanalysis*
7. *Learning a SAT Solver from Single-Bit Supervision* (NeuroSAT)
8. *Improved Attacks on GIFT-64*
9. *Key-Recovery Attacks on CRAFT and WARP*

The CRAFT/WARP supplementary README identifies the associated main paper as
*Key-Recovery Attacks on CRAFT and WARP*. The full-version paper is now
available at `../papers/04_cipher-extensions/15_key_recovery_attacks_craft_warp.pdf`.
The repository assessment below still distinguishes the paper from the
supplementary README, pattern PDFs, source ZIP inventories, and staged source
code.

## 2. Overall relationship

```text
                            Exact verification boundary
                                       |
                                       v
                    +------------------------------------+
                    | Exact SAT baseline                 |
                    | Accelerating Automatic Search      |
                    +------------------+-----------------+
                                       |
                          exact instances, bounds,
                          labels and solver outcomes
                                       |
              +------------------------+------------------------+
              |                                                 |
              v                                                 v
+-----------------------------+                  +-----------------------------+
| A. Differential-level       |                  | B. ML-guided SAT search     |
| analysis pipeline           |                  |                             |
|                             |                  | Accelerating                |
| GIFT-64 Differential        |                  |   -> BAKSHEESH              |
|   -> Accelerating           |                  |   -> NeuroGIFT-V1*          |
|   -> Improved Attacks       |                  |   -> GIFT-64 Differential   |
|   -> CRAFT/WARP             |                  +--------------+--------------+
+--------------+--------------+                                 |
               |                                                |
               | exact trails, constraints,                     | ranking,
               | right-key spaces, probability                  | prioritisation,
               | and coexistence results                        | runtime prediction
               |                                                |
               +----------------------+-------------------------+
                                      |
                                      v
                         Exact SAT re-verification
                                      |
                                      v
                              Verified result

* Repository is referenced but its code is empty/not present locally.
```

The differential-level pipeline is the exact backbone. ML is an optional search
aid; it must not replace exact SAT validation for trails, bounds, key spaces,
probabilities, coexistence, or optimality claims.

## 3. Research line A: Differential-level analysis pipeline

### Recommended reading order

1. `Supplementary_Material_GIFT-64_Differential`
2. `Accelerating_Automatic_Search`
3. `Improved_Attacks_GIFT64`
4. `CRAFT-and-WARP`

### Roles

| Repository | Role |
|---|---|
| GIFT-64 Differential | Direct experimental material for the newest trail-to-differential pipeline |
| Accelerating Automatic Search | SAT-search foundation and a reference for code/solver organisation |
| Improved Attacks GIFT64 | Historical attack paper plus two small SAT searches; supports encoding/result regression, but not complete paper reproduction |
| CRAFT-and-WARP | Cross-cipher and related-tweak-key portability evaluation |

### Likely engineering outcome

A research-side CLI/API that wraps the currently separate GIFT-64 stages and
adds:

- explicit configuration and provenance;
- versioned trail, constraint, right-key-space and probability schemas;
- deterministic seeds and resource limits;
- cache keys based on inputs/configuration/solver version;
- structured logs and resumable stages;
- a result database containing summaries and hashes, not generated CNF or raw
  solver logs in Git;
- cipher adapters and portability interfaces.

The wrapper should call upstream through narrow adapters and must not copy or
modify the upstream repositories.

## 4. Research line B: ML-guided SAT search

### Recommended reading order

1. `Accelerating_Automatic_Search`
2. `Supplementary_Material_BAKSHEESH`
3. `NeuroGIFT-V1` - obtain and scan first
4. `Supplementary_Material_GIFT-64-Differential`

### Roles

| Repository | Role |
|---|---|
| Accelerating Automatic Search | Generate SAT instances, exact labels and solver baselines |
| BAKSHEESH | First familiar experimental object and a compact transfer benchmark |
| NeuroGIFT-V1 | Prior ML design and possible entry point to unpublished code/data/models; not locally verified |
| GIFT-64 Differential | More complex downstream ML application and integration scenario |

The critical confirmed gap is that the public BAKSHEESH repository contains
only the cipher implementation. It does not contain the characteristic-search
code used to confirm optimal bounds or enumerate the 3072 optimal
characteristics.

Recommended ML task order:

1. exact-solver runtime/difficulty prediction;
2. candidate or partial-trail ranking;
3. solver/configuration portfolio selection;
4. branch or phase hints with complete fallback search;
5. only later, approximate SAT/UNSAT classification.

## 5. Upstream repository inventory

### 5.1 Supplementary Material: GIFT-64 Differential

**Research support:** primary source for line A; later exact-label/application
source for line B.

| Stage | Entry | Inputs | Outputs | Dependencies | Missing content |
|---|---|---|---|---|---|
| Trail search | `Source_code/1.Searching_for_trails_contained_in_a_differential/main.cpp` | Hard-coded `ObjectiveProb`, `trailround`, `GroupIndex`, differential/key-difference tables | `TrailInformation.out`; trail details/counts/runtime on stdout | C++11, CryptoMiniSat 5 C++ API | CLI/config, all-group driver, output schema, deduplication and expected hashes |
| Linear constraints | `Source_code/2.Finding_linear_constraints/main.cpp` | Included `TrailInformation.out` | LaTeX-like LC equations on stdout | Standard C++ | Structured LC output and affine-space equivalence tests |
| Linearised nonlinear constraints | `Source_code/3.Finding_linearized_nonlinear_constraints/main.cpp` | Included `TrailInformation.out` | LNC equations on stdout | Standard C++ | Structured LNC output and exact paper-section provenance |
| Stage 2 validation | `Source_code/4.Stage2_test/main.cpp` | Included `TrailInformation.out`; absent `KeyCandidate.out` | Per-key/trail SAT result and runtime on stdout | C++11, CryptoMiniSat 5 | `KeyCandidate.out` generator, seed, schema and hash |
| Stage 3 probability | `Source_code/5.Stage3_test/main.cpp` | Included `TrailInformation.out` and `KeyCandidate1000.out` | Solution counts and runtime on stdout | C++11, CryptoMiniSat 5, `std::random_device` | Deterministic seed, statistical contract/confidence bounds and structured output |
| Trail coexistence | `Source_code/6.Checking_the_simultaneous_validity_of_trails/main.cpp` | Included `AllMatrix33Trail.out` | Compatible trail sets/counts on stdout | C++11, CryptoMiniSat 5 | Generator/schema for the 739 x 185 matrix and link from minor-trail enumeration |

Repository-wide gaps:

- no build system or end-to-end driver;
- hard-coded parameters, filenames and stage connections;
- no versioned artifact schemas or automated tests;
- no code-level mapping from configurations to paper tables/figures;
- no identified generator for the 18/19-round extensions;
- missing generation paths for `KeyCandidate.out` and
  `AllMatrix33Trail.out`.

### 5.2 Accelerating Automatic Search

**Research support:** SAT foundation for both lines, especially the exact
baseline and label-generation boundary.

| Item | Finding |
|---|---|
| Entries | Ten `SearchWithCadical.py` scripts: four PRESENT, four LBlock and two SIMON objectives |
| Core logic | Cipher-specific round encoding, sequential-counter objective, Matsui bounding conditions and iterative SAT/UNSAT bound search |
| Inputs | No CLI; cipher settings, round range, existing bounds and solver path are source constants |
| Intermediate outputs | `Problem-Round*.cnf`, solver `*-solution.out`, temporary `SatSolution.out` and `UnsatSolution.out` |
| Persistent outputs | `MatsuiCondition.out`, `RunTimeSummarise.out` and stdout |
| Dependencies | Python standard library, CaDiCaL, `sed`, `rm` |
| Environment assumptions | CaDiCaL path is hard-coded as `~/Install/cadical/build/cadical` or `/dataspace/cadical/build/cadical` |
| Missing content | Solver adapter, CLI/config, schemas, tests, manifests, robust status/error handling and code for several paper ciphers |

The best first entry is:

`1.Source-Code/1.PRESENT/1.Differential-Active-Sbox/SearchWithCadical.py`.

It is smaller than the GIFT pipeline and exposes the key contracts needed for a
general exact baseline: objective, CNF, bound, solver invocation, SAT/UNSAT
status, runtime and temporary-file lifecycle.

### 5.3 Supplementary Material: BAKSHEESH

**Research support:** compact exact benchmark and first ML transfer object, but
not a search-code source.

| Item | Finding |
|---|---|
| Entry | `main.cpp` |
| Core modules | `KeySchedule`, `BAKSHEESH_Enc`, S-box, 35 round constants and 128-bit permutation |
| Input | Fixed plaintext and key in `main()` |
| Output | Ciphertext words on stdout |
| Dependencies | Standard C++ only |
| Missing content | SAT/CNF generator, optimal linear-characteristic search, active-S-box bound search, 3072-characteristic enumerator, CLI, tests, build file and result schema |

Useful paper oracles, once the search is independently rebuilt:

- `|Cor(R)| = 2^(-3R+2)` for `R >= 12`;
- a unique one-round iterative optimal structure;
- 3072 optimal `R`-round linear characteristics for `R >= 12`.

The representation boundary needs special care: paper notation, designer
notation, upstream word/nibble reversal and future SAT variable indices must be
made explicit and tested.

### 5.4 CRAFT and WARP

**Research support:** final line-A portability target and possible
out-of-distribution line-B test.

| Item | Finding |
|---|---|
| Entries | `3.CRAFT-Source-Code.zip` and `5.WARP-Source-Code.zip` |
| Core modules | Step 0 right-pair generation; Steps 1-7 staged forward/backward partial-key filtering and remaining-key checks |
| Inputs | Many hard-coded keys, right pairs and attack parameters; WARP additionally includes several staged candidate `.out` files |
| Outputs | `MemoriseRightPair.out`, repeated `MemoriseKeyCandidate.out` files and stdout candidate/runtime summaries |
| Dependencies | Standard C++ and shell tools; the staged C++ does not invoke a SAT solver |
| Nondeterminism/concurrency | Step 0 uses `srand(time(0))`; CRAFT Step 5 launches 16 background cases through `SetUpTest.sh` |
| Missing content | Formal stage graph, build/run documentation, expected outputs/runtimes, complete candidate provenance, deterministic controls and small fixtures |

This repository is key-recovery supplementary material, not a second copy of
the GIFT differential pipeline. It should be introduced only after general
trail/key/tweak/candidate interfaces are stable.

### 5.5 Improved Attacks GIFT64 archive

**Research support:** small historical SAT regression cases for line A; not a
complete attack implementation.

| Item | Finding |
|---|---|
| Archive | `../upstream/_archives/Improved_Attacks_GIFT64-main.zip`, commit metadata `0dff1caf65675de6ab0aa7edf0f51883a576eacc` |
| Entries | `Differential.cpp` and `Linear.cpp` |
| Differential search | Four GIFT-64 rounds; hard-coded integer weight 11 and decimal-weight component 1 |
| Linear search | Five GIFT-64 rounds; hard-coded best weight 7 |
| Core logic | GIFT-64 bit permutation, S-box differential/linear CNF clauses, sequential-counter cardinality bound, one CryptoMiniSat solve |
| Inputs | None at runtime; all round counts, bounds and transition constraints are compiled into the source |
| Outputs | One satisfying trail's per-round `xin`/`xout` values on stdout; no structured file |
| Dependencies | C++11 and CryptoMiniSat 5 C++ API |
| Missing content | README, build instructions, command-line parameters, UNSAT/UNKNOWN reporting, expected output, tests, attack code and mapping to a particular paper table/result |

The archive supports regression of two small historical search configurations.
The associated paper states that its search source code is public, but the
archive does not expose the paper-scale loops, data or manifests needed to
reproduce:

- exhaustive enumeration of 5120 optimal 12-round linear trails;
- grouping/evaluation of their linear approximations and ELPs;
- enumeration of 92768 weight-64 13-round differential trails;
- grouping/evaluation of 2392 differentials;
- the selected L16/D03 distinguishers from a structured result artifact;
- the 19-round linear or 20-round differential key-recovery computations.

It also does not contain key recovery, attack-complexity evaluation,
differential aggregation or a result manifest. It therefore cannot by itself
provide paper-level or attack-level regression.

## 6. Paper conclusions

| Paper | Main conclusion | Research support |
|---|---|---|
| Accelerating SAT | Reuses sequential-counter variables to encode Matsui bounds without a second objective encoding; exact soundness/completeness is retained while many searches accelerate | Exact SAT baseline for A and B; later label generator |
| GIFT-64 from trails to differentials | Moves the attack object from one trail to right-key space plus remaining differential probability; identifies 32 dominant cores, disjoint right-key spaces within classes and minor-trail coexistence via Max-PoSSo | Primary specification for A; complex application for B |
| Linearisation method | Defines LNCs and a three-stage evaluation: LC/LNC initial space, SAT validation, then remaining-probability estimation | Core constraint/probability stages of A |
| LED64/Midori64 | Shows that simply summing trail probabilities can be misleading under fixed keys; studies right pairs, weak-key ratios and compatible trails via SAT/Max-PoSSo | Methodological predecessor for A |
| BAKSHEESH optimal characteristics | Proves the long-round correlation formula, structure and count 3072, but the public repository lacks the search implementation | Exact benchmark for A infrastructure and B transfer |
| NeuroGIFT | Specialising NeuroSAT to structured GIFT instances improves its reported scaling/accuracy, but shortcut learning, assignment recovery, approximation and graph memory remain unresolved | Primary line-B task/risk reference |
| NeuroSAT | A literal-clause message-passing network can learn SAT-related search behavior from a single label, but remains much less reliable than production SAT solvers | Architectural foundation for B, never the verifier |
| Improved Attacks on GIFT-64 | Reports 5120 optimal 12-round linear trails, a first 19-round linear attack, 92768 weight-64 13-round differential trails grouped into 2392 candidate differentials, and a first 20-round differential attack without the full codebook | Historical line-A attack target and regression source; public archive covers only two small encoding examples |

Important methodology caveat: the Linearisation paper explicitly notes that
its empirical probability estimates lack the statistical guarantees of
PAC-style approximate model counting. Probability stages should therefore
record sampling assumptions and uncertainty rather than report point estimates
as exact facts.

## 7. Two research workstreams and their enabling milestones

The project has **two research goals**, not five independent research goals:

### Workstream A: Automated Differential-Level Analysis Pipeline

This is the primary research and engineering line, directly motivated by
*A Deeper Look at Related-Key Differentials of GIFT-64: From Trails to
Differentials*.

```text
GIFT trail search
  -> trail enumeration/grouping
  -> LC/LNC extraction
  -> initial right-key space
  -> exact fixed-key validation
  -> remaining-probability evaluation
  -> trail coexistence / Max-PoSSo
  -> differential construction
  -> reproducible report
```

The first concrete deliverable should therefore be a bounded, reproducible
GIFT-64 pipeline slice. `Accelerating_Automatic_Search` supplies its exact SAT
foundation; `Improved_Attacks_GIFT64` supplies two small historical regression
cases and its paper supplies historical attack targets; CRAFT/WARP is a later
portability check.

### Workstream B: ML-Guided SAT Search

This is the second research line:

```text
exact SAT instance/label generation
  -> candidate or partial-trail representation
  -> runtime prediction / ranking / solver guidance
  -> exact SAT re-verification
  -> measured time-to-validated-result
```

`Accelerating_Automatic_Search` supplies exact instances and labels.
BAKSHEESH is a compact first benchmark. NeuroGIFT/NeuroSAT supply the prior ML
ideas and risks. GIFT-64 is the later complex integration target.

### Why the earlier five-stage order appeared

The sequence

```text
SAT baseline
  -> GIFT-64 pipeline
  -> BAKSHEESH benchmark
  -> ML-guided SAT
  -> CRAFT/WARP portability
```

is an **implementation dependency order**, not the scientific-priority map:

- SAT baseline is shared infrastructure needed to trust both workstreams;
- GIFT-64 pipeline is the first main research deliverable in workstream A;
- BAKSHEESH is the smallest exact benchmark needed before training/evaluating
  workstream B;
- ML-guided SAT is workstream B itself;
- CRAFT/WARP is cross-cipher validation after the interfaces stabilise.

A clearer project view is:

```text
Shared exact SAT/provenance contract
          |
          +--> Workstream A: GIFT differential-level pipeline
          |         |
          |         +--> Improved-Attacks regression
          |         +--> CRAFT/WARP portability
          |
          +--> Workstream B: BAKSHEESH exact benchmark
                    |
                    +--> ML-guided SAT
                    +--> GIFT integration / cross-cipher transfer
```

The SAT baseline should remain a small prerequisite inside the two workstreams,
not become a separate research topic that delays the GIFT pipeline.

## 8. Stage-contract schema design

The schema is not one large database schema. It is a set of versioned contracts
at the boundaries between exact pipeline stages. The canonical definitions
should eventually live under `src/shared/`; pipeline and ML modules should both
consume them. This section defines the required content but does not implement
it.

### 8.1 Common artifact envelope

Every artifact type must carry:

| Field | Purpose |
|---|---|
| `schema_version` | Allows compatible parsing and explicit migrations |
| `artifact_id`, `artifact_type` | Stable identity and type |
| `parent_artifact_ids` | Complete stage lineage |
| `created_at` | Audit timestamp, not part of deterministic content hash |
| `cipher`, `variant`, `analysis_kind` | For example GIFT-64, related-key, differential |
| `round_start`, `round_end`, `round_count` | Avoids ambiguous “8/8.25 round” interpretation |
| `state_layout_id`, `bit_order_id`, `nibble_order_id` | Makes representation conventions explicit |
| `source_repository`, `source_commit`, `entry_point` | Upstream provenance |
| `config_hash`, `input_hashes` | Cache/reproduction identity |
| `tool_version`, `host_profile` | Tool provenance; host data should avoid personal identifiers |
| `seed`, `time_limit_s`, `memory_limit_mb` | Reproducibility/resource boundary |
| `validation_status` | `unvalidated`, `partially_validated`, or `exact_validated` |

Large CNF files, key lists, logs and model outputs remain external artifacts.
The contract stores their content hash, byte size, format and relative artifact
reference; it does not place them in Git.

### 8.2 `SolverRequest` and `SolverResult`

This is the first schema boundary because it supports both research lines.

`SolverRequest` must include:

- problem kind and encoding version;
- cipher/round configuration;
- objective (`active_sboxes`, `weight`, `probability`, `bias`, coexistence);
- bound and comparison semantics (`<`, `<=`, `=`, `>=`);
- assumptions and fixed input/output differences;
- CNF/XOR-CNF artifact hash and variable-map hash;
- solver/configuration, seed and resource limits.

`SolverResult` must include:

- status: `SAT`, `UNSAT`, `UNKNOWN`, `TIMEOUT`, `ERROR`;
- whether the result is definitive for the requested bound;
- model/proof artifact references and hashes;
- objective value and satisfied bound;
- wall/CPU time, peak memory and solver statistics;
- exit code and parse diagnostics;
- independent verification result;
- exact label allowed for ML: yes/no and reason.

### 8.3 `TrailRecord` and `TrailSet`

This connects trail search to LC/LNC extraction and later grouping.

Required fields:

- `trail_id`, `differential_id`, group/class and canonicalisation key;
- cipher, key relation and master-key difference;
- input/output difference for the whole trail;
- per-round `xin`, `xout`, round-key difference and S-box transitions;
- round numbering and explicit 8.25-round boundary semantics where applicable;
- active-S-box count, integer/decimal weight components, claimed probability;
- exact solver-result reference;
- duplicate/equivalence relation to other trails;
- source group/index and upstream text-record location.

`TrailSet` adds ordering, membership, enumeration completeness and grouping
criteria. It must distinguish “one model found”, “all models under a bound” and
“a sampled subset”.

### 8.4 `ConstraintSet`

LC and LNC use one structural contract with different `constraint_kind` values:

- `LC`;
- `LNC`;
- `additional_exact_constraint`;
- `uncategorised_nonlinear_constraint`.

Required fields:

- field/ring, normally `GF(2)`;
- canonical variable IDs and their cipher/round/key-bit meanings;
- coefficient matrix/equations and right-hand side;
- affine offset, rank, nullity, pivot/free variables and chosen basis;
- source trail, rounds, active S-boxes and derivation method;
- semantic hash of the represented affine space;
- equivalence-check result against another basis;
- exact/heuristic derivation status.

The semantic affine-space hash/equivalence result is important because Gaussian
elimination may produce a different basis/order while representing the same
constraint space.

### 8.5 `RightKeySpace`

This represents both the Stage 1 initial space and the Stage 2 validated space.

Required fields:

- `key_space_id`, master-key width and key-bit ordering;
- representation kind: affine equations, explicit candidate-set reference,
  predicate, or union of spaces;
- source LC/LNC constraint-set IDs;
- dimension/codimension and exact or estimated cardinality;
- initial versus validated status;
- validation method, solver-result references and checked-key count;
- sampling frame, seed and candidate-file hash when sampling is used;
- discovered additional constraints or contradictions;
- intersection/union/disjointness relations with other trail key spaces;
- validation coverage and limitations.

Million-key candidate files must remain external and content-addressed. A
`RightKeySpace` must not imply exact completeness when it was validated only by
sampling.

### 8.6 `ProbabilityEstimate`

Required fields:

- target trail/differential ID;
- conditioning `RightKeySpace` ID;
- probability semantics: Markov estimate, fixed-key probability, remaining
  probability, empirical differential probability, or exact/model count;
- method: exact count, approximate model count, simulation or sampling;
- trials/sample count, successes and rejected samples;
- point estimate, confidence interval and confidence level;
- epsilon/delta for PAC-style approximate counting when applicable;
- seed, sampling plan, stopping rule and resource budget;
- aggregation rule over trails and coexistence assumptions;
- exact/empirical status and known statistical limitations.

The schema must prevent an empirical Stage 3 estimate from being displayed as
an exact probability.

### 8.7 Minimal implementation order

Only the following contracts are needed initially:

1. common artifact envelope;
2. `SolverRequest` / `SolverResult`;
3. `TrailRecord` / `TrailSet`;
4. `ConstraintSet`;
5. `RightKeySpace`;
6. `ProbabilityEstimate`.

Do not begin with cache tables, a results database or ML feature schemas. Those
should be derived after the stage contracts and representation conventions are
stable.

## 9. First files to read

### For line A

1. `../upstream/Supplementary_Material_GIFT-64_Differential/Source_code/README.md`
2. `../papers/01_gift-pipeline/01_deeper_look_related_key_differentials_gift64.pdf`,
   Sections 2-4
3. `../papers/01_gift-pipeline/03_linearisation_method_differential_dependencies.pdf`,
   Sections 4-6
4. the six GIFT `Source_code/*/main.cpp` files in order
5. `../upstream/Accelerating_Automatic_Search/ReadMe.pdf`
6. the Accelerating paper's SAT encoding and Matsui-bound sections
7. `../upstream/Accelerating_Automatic_Search/1.Source-Code/1.PRESENT/1.Differential-Active-Sbox/SearchWithCadical.py`
8. `../papers/01_gift-pipeline/07_12_19_improved_attacks_gift64.pdf`,
   especially Sections 2.2, 3.1 and 4.1
9. `../upstream/_archives/Improved_Attacks_GIFT64-main.zip` members `Differential.cpp` and
   `Linear.cpp`

Use the two `Improved_Attacks_GIFT64` programs as historical SAT regression
cases only. They are insufficient for a complete paper/attack regression.

### For line B

1. the same small PRESENT `SearchWithCadical.py`
2. `../upstream/Supplementary_Material_BAKSHEESH/main.cpp`
3. `../papers/04_cipher-extensions/05_optimal_linear_characteristics_baksheesh.pdf`,
   especially the representation section and structural/counting results
4. the NeuroSAT architecture section
5. the NeuroGIFT dataset construction, controlled-negative and limitations
   sections

After that, obtain `NeuroGIFT-V1` before deciding the ML implementation path.

## 10. Immediate next actions

Still read-only:

1. obtain or confirm the status of `NeuroGIFT-V1`, including code, data
   generator, datasets, checkpoints, license and commit;
2. ask for the missing BAKSHEESH characteristic-search code;
3. ask for the GIFT `KeyCandidate.out` generation method, seed and schema;
4. obtain the main *Key-Recovery Attacks on CRAFT and WARP* paper;
5. determine whether more code/results exist behind the two-file
   `Improved_Attacks_GIFT64` archive, especially the 12/13-round enumeration,
   grouping, ELP/probability evaluation and key-recovery code;
6. define the smallest expected public fixture for each exact stage before any
   implementation begins.

## 11. Reported compute environments and server scaling

The papers support the following claims only; they do not establish the
authors' current private machine configuration.

| Source | Reported environment | Workload |
|---|---|---|
| *A Deeper Look at Related-Key Differentials of GIFT-64* (2026) | 24-core Apple M2 Ultra; every test run single-threaded | Stage 2 validation of all 32 trails took 59.81 hours |
| *A Linearisation Method...* (2026) | Desktop with Apple M2 Ultra; reported runtimes use one core | CryptoMiniSat-based three-stage evaluation |
| *Improved Attacks on GIFT-64* (2021) | One processor/core of an AMD EPYC 7302 16-core server | Exhaustive L16 trail search above the stated correlation threshold took about 10 hours |
| *Accelerating the Search...* (2021) | Intel Core i5-9400F @ 2.90 GHz, one core | SAT-search runtime comparisons |
| *NeuroGIFT* | GTX 970 GPU; graph generation exceeded memory above seven rounds in the reported setup | Neural literal-clause graph training/inference |

### Best server parallelisation boundary

Most benefit should come from running independent exact jobs concurrently, not
from assigning all cores to one SAT instance:

- GIFT groups, trails and sampled keys are independent at several stages;
- Stage 2's 32 trail validations can be distributed as separate jobs;
- Stage 3 key/sample evaluations are highly parallel;
- benchmark instances and ML label generation are independent;
- CRAFT/WARP case directories can be isolated and scheduled independently.

LC/LNC Gaussian elimination is unlikely to benefit materially from a large
server. A single hard SAT/Max-PoSSo instance may benefit from solver
multithreading and more RAM, but scaling is solver/instance dependent and can
reduce reproducibility. Instance-level parallelism with one pinned core per
solver process should be the first benchmark.

For exact work, a many-core CPU server with ample RAM and local NVMe storage is
the natural target. For ML-guided SAT, a separate NVIDIA GPU with substantially
more memory than the historical GTX 970 is useful, but larger memory alone does
not remove NeuroGIFT's graph-size/representation problem.

Any comparison must record solver version, thread count, CPU model, memory,
timeout, seed and instance hash. Runtime numbers from M2 Ultra, EPYC and older
Intel systems must not be compared as algorithmic speedups without rerunning
the same instances and configurations.
