# Materials and Dependency Status

> Last updated: 2026-07-26
>
> Status vocabulary:
>
> - `available`: present and inspected locally;
> - `partial`: present but incomplete for the intended claim;
> - `missing-blocking`: absent and blocks the stated milestone;
> - `missing-nonblocking`: absent but work can continue on a smaller scope;
> - `deferred`: intentionally not needed yet.

## Summary

The current workspace is sufficient to:

- execute and independently validate the controlled GIFT-64 four-round SAT
  baseline;
- parse and structurally validate the supplied GIFT `TrailInformation.out`
  corpus through a versioned contract;
- reproduce and normalize the pinned LC program's equations through a
  versioned GF(2) contract;
- reproduce and normalize the pinned LNC-stage combined spaces and compare
  them algebraically against the LC bases;
- generate a new deterministic key corpus for a controlled Stage 2 demo;
- execute a hash-pinned, per-key-bounded Stage 2 demo for one explicitly
  selected physical trail-record position;
- build small parser and verifier fixtures that do not invoke a solver.

It is not sufficient to reproduce the complete GIFT differential-level paper.

## Shared exact SAT foundation

| Material | Status | Local evidence | Needed for | Action |
|---|---|---|---|---|
| Accelerating SAT paper | available | `../papers/accelerating-search/01_accelerating_search_differential_linear_sat.pdf` | Encoding/bounding-condition reference | None |
| Accelerating source | available | `../upstream/Accelerating_Automatic_Search/` | Legacy CaDiCaL baseline | Keep read-only |
| Improved Attacks paper | available | `../papers/gift64-improved-attacks/01_improved_attacks_gift64.pdf` | Historical GIFT search/attack targets | None |
| Improved Attacks source archive | partial | `../upstream/_archives/Improved_Attacks_GIFT64-main.zip`; extracted read-only source in `../upstream/Improved_Attacks_GIFT64/` | First GIFT SAT baseline | Use only as two small search references |
| Versioned solver contracts | available | `src/shared/sat/contracts.py`; GIFT request under `experiments/gift64/` | Shared exact boundary for both workstreams | Extend only when a concrete stage requires new fields |
| Independent GIFT-64 verifier | available | `src/shared/ciphers/gift64.py`; structural, negative and controlled-result tests | Validate decoded four-round trails without solver trust | None for the four-round baseline |
| Controlled GIFT-64 adapter | available | `src/automated_differential_analysis/adapters/gift64_improved_legacy.py` | Explicit status, decode, verification and result contract | None for the four-round baseline |
| Normalized GIFT-64 regression | available | `experiments/gift64/sat_baseline_b6.regression.json`; temporary end-to-end checker | Stable semantic oracle without generated output | Revisit model-hash policy only after explicit seed control |
| C++ compiler | available | `/usr/bin/clang++`, `/usr/bin/g++` | Native adapter/baseline compilation | None |
| CryptoMiniSat 5 executable/API | available | Homebrew CryptoMiniSat `5.14.7`; GMP `6.3.0` | Compile and run GIFT/Improved C++ SAT code | C++17 and explicit Homebrew include/lib prefixes required |
| CaDiCaL | missing-nonblocking | Not found in PATH | Execute Accelerating Python scripts | Defer until CaDiCaL baseline is selected |
| Exact solver version used by each paper | partial | Papers identify solver families; local baseline now records CryptoMiniSat `5.14.7` | Fair runtime/result comparison | Treat historical runtime as non-comparable |
| Expected output for four-round Improved differential search | available | B6 compact expectation requires verified `SAT` and components `11`/`1`; raw output remains untracked | Regression oracle | None |

## Workstream A: GIFT differential-level pipeline

| Material | Status | Local evidence | Needed for | Action |
|---|---|---|---|---|
| Main GIFT differential paper | available | `../papers/gift64-differential/01_deeper_look_related_key_differentials_gift64.pdf` | Pipeline target/results | None |
| Linearisation paper | available | `../papers/gift64-differential/02_linearisation_method_differential_dependencies.pdf` | LC/LNC and three-stage evaluation | None |
| LED64/Midori64 paper | available | `../papers/gift64-differential/03_more_accurate_differential_properties_led64_midori64.pdf` | Max-PoSSo/fixed-key method history | None |
| Six GIFT stage programs | available | `../upstream/Supplementary_Material_GIFT-64_Differential/Source_code/` | Direct pipeline reference | Keep read-only |
| `TrailInformation.out` | available | Four byte-identical stage 2-5 copies; `gift64-trail-information/v1` parser and tests | Normalized LC/LNC input fixture | Preserve source hash; request trail-selection/concatenation provenance |
| Trail selection/group manifest | missing-nonblocking | Producer handles one `GroupIndex`; bundled corpus contains eight positional groups in a different order | Exact regeneration of the 32-trail fixture | Obtain commands, seeds, selection rule and position-to-`GroupIndex` map |
| LC equations and supplement | available | Pinned LC source; one-page eight-set PDF; `constraint-set/v1` observation yields 32 rank-6 spaces | Structured Stage 1 LC boundary | Add an independent derivation after LNC semantics are stable |
| Independent LC derivation | missing-nonblocking | Current adapter exactly observes legacy matrices but does not independently recompute them | Stronger algorithmic verification | Reimplement/test DDT affine spaces and elimination separately |
| LNC-stage equations | available | Pinned LNC source; combined `constraint-set/v1` spaces yield rank 8 and imply every rank-6 LC base with incremental rank 2 | Structured linearised-relation boundary | Add an independent `DDTInOutRelation` derivation later |
| Generated Stage 2 demo corpus | available | `gift64-stage2-key-corpus/v1`; domain-separated SHA-256 counter generator and tracked eight-key request | Controlled fixed-key demonstration | Keep generated corpus/result files out of Git and retain `generated-for-demo` label |
| `KeyCandidate1000.out` | available | Included in GIFT stage 5 | Stage 3 input fixture | Recover format and provenance limitations |
| `KeyCandidate.out` | missing-blocking | Referenced by stage 4, not included; A4 replaces it only with a labelled temporary demo corpus | Paper-level Stage 2 reproduction | Obtain generator, distribution, seed and hash |
| `AllMatrix33Trail.out` | partial | Included in GIFT stage 6 | Coexistence input fixture | Generator and semantic schema are missing |
| Minor-trail enumeration/generator | missing-blocking | No complete path found | Reproduce minor-trail accumulation | Ask for code/config/results provenance |
| 18/19-round extension generator | missing-blocking | No entry found | Reproduce 128 reported extensions | Ask for code or formal construction procedure |
| Program/config-to-paper-result map | missing-nonblocking | Functional correspondence inferred only | Paper-level regression | Build bounded mapping; request author confirmation |
| CRAFT/WARP main paper | missing-nonblocking | Only supplementary README/patterns/source ZIPs present | Later portability interpretation | Obtain before portability implementation |

## Improved Attacks regression material

| Material | Status | Local evidence | Needed for | Action |
|---|---|---|---|---|
| `Differential.cpp` | partial | Archive member; fixed four rounds and fixed split weight bound | Small differential encoding baseline | Use as baseline source |
| `Linear.cpp` | partial | Archive member; fixed five rounds and weight 7 | Small linear encoding regression | Defer until differential baseline passes |
| 12-round linear enumeration code/data | missing-blocking | Not in archive | Reproduce 5120 trails | Ask whether additional source exists |
| Linear approximation grouping/ELP evaluation | missing-blocking | Not in archive | Reproduce L16 selection | Ask for code/results |
| 13-round differential enumeration code/data | missing-blocking | Not in archive | Reproduce 92768 trails/2392 differentials | Ask for code/results |
| 19/20-round key-recovery implementation | missing-blocking | Not in archive | Attack-level regression | Ask for code or treat paper calculations as reference only |

## Workstream B: BAKSHEESH exact benchmark

| Material | Status | Local evidence | Needed for | Action |
|---|---|---|---|---|
| BAKSHEESH paper | available | `../papers/baksheesh/01_optimal_linear_characteristics_baksheesh.pdf` | Exact long-round oracles | None |
| Cipher implementation | available | `../upstream/Supplementary_Material_BAKSHEESH/main.cpp` | Cipher/ordering/test-vector boundary | Keep read-only |
| Original SAT/characteristic search code | missing-blocking | Public repository contains encryption only | Direct original-method reproduction | Ask author or rebuild independently |
| 3072-characteristic list/generator | missing-blocking | Count and construction described; artifact absent | Full enumeration oracle | Request artifact or formalise independent generator |
| Bit/nibble ordering map | partial | Can be inferred from paper and source | Correct SAT variables and tests | Document and test before encoding |

## Workstream B: ML-guided SAT

| Material | Status | Local evidence | Needed for | Action |
|---|---|---|---|---|
| NeuroSAT paper | available | `../papers/ml-guided-sat/02_neurosat_single_bit_supervision.pdf` | Architecture reference | None |
| NeuroGIFT paper | available | `../papers/ml-guided-sat/01_neurogift_ml_sat_cryptanalysis.pdf` | Task/data/risk reference | None |
| NeuroGIFT-V1 source | missing-blocking | Reported by user as empty/not available | Direct prior-code reproduction | Confirm whether code can be obtained |
| NeuroGIFT data generator/datasets | missing-blocking | Not present | Reproduce published classification | Request or create new exact-labelled dataset later |
| Checkpoints/training config | missing-blocking | Not present | Published-model comparison | Request; otherwise define a new baseline |
| Exact labels and split manifest | partial | One B5 GIFT result exercises exact-label gating; no dataset/split exists | New ranking/runtime work | Build a bounded labelled corpus only after benchmark design |
| NVIDIA GPU environment | deferred | No approved environment configured | ML training | Select only after task/data contract exists |

## Portability: CRAFT/WARP

| Material | Status | Local evidence | Needed for | Action |
|---|---|---|---|---|
| Supplementary repository | available | `../upstream/CRAFT-and-WARP/` | Source/pattern inventory | Keep read-only |
| CRAFT/WARP source ZIPs | available | `3.CRAFT-Source-Code.zip`, `5.WARP-Source-Code.zip` | Later adapters | Extract only to temporary directories |
| Main paper | missing-blocking | Not present | Correct Step0-Step7/result mapping | Obtain before implementation |
| Candidate provenance/expected outputs | partial | Some WARP candidate files included | Reproducible staged run | Recover formal stage manifest |
| Runtime/resource specification | missing-nonblocking | Not reported locally | Safe benchmark execution | Obtain before any long run |

## Compute/server material

No server material is required for the current static baseline work.

Before server execution, record:

- CPU/GPU model, physical/logical cores and RAM;
- operating system and compiler;
- solver/library versions;
- scheduler/job isolation;
- local scratch/output paths;
- per-job core, memory and time limits;
- instance/config hashes and deterministic seeds.

Do not place credentials, hostnames containing personal information, or private
access tokens in this repository.
