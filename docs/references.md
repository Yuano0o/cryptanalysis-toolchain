# References

Everything this toolchain builds on is published material. The reference
implementations are reached through adapters and are never vendored or modified;
see [design notes](design.md) for how that boundary works.

## Methods

| Work | Role here |
| --- | --- |
| Sun, L., Wang, W., Wang, M. *Accelerating the Search of Differential and Linear Characteristics with the SAT Method.* IACR Transactions on Symmetric Cryptology, pp. 269–315 (2021) | SAT encoding and bounding-condition reference for the solver baseline |
| *Improved Attacks on GIFT-64* (2021) | Historical GIFT-64 search and attack targets; source of the four-round differential encoding used as the regression baseline |
| *A Deeper Look at Related-Key Differentials of GIFT-64* (2026) | The differential-level pipeline this toolchain reproduces stage by stage |
| *A Linearisation Method for Differential Dependencies* (2026) | Linear and linearised-nonlinear constraint semantics used in stages 2 and 3 |
| *More Accurate Differential Properties of LED64 and Midori64* | Method history for fixed-key and Max-PoSSo style evaluation |
| Peng, Y., Liu, J., Sun, L. *Investigation of the Optimal Linear Characteristics of BAKSHEESH.* ICISC 2024, LNCS 15596, pp. 18–32, Springer (2025). [DOI](https://doi.org/10.1007/978-981-96-5566-3_2) · [IACR ePrint 2024/1801](https://eprint.iacr.org/2024/1801) | Exact long-round oracles for the planned BAKSHEESH benchmark |
| *Key Recovery Attacks on CRAFT and WARP* | Target semantics for the deferred portability work |

## Machine-learning prior work

The learned-guidance workstream is designed but not implemented. These are
recorded as design constraints, not as reproduced results.

| Work | Role here |
| --- | --- |
| Selsam, D. et al. *Learning a SAT Solver from Single-Bit Supervision* (NeuroSAT) | Architecture reference for candidate scoring |
| NeuroGIFT — machine learning for SAT-based cryptanalysis | Task formulation, dataset requirements and reported limitations |

## Reference implementations

Accessed read-only through adapters, with a pinned source hash checked before
every run. None of this code is copied into this repository.

| Source | Used for |
| --- | --- |
| Supplementary material for *A Deeper Look at Related-Key Differentials of GIFT-64* — six stage programs | The primary pipeline: trail search, linear constraints, linearised constraints, fixed-key validation, probability evaluation, coexistence |
| Supplementary archive for *Improved Attacks on GIFT-64* (`Differential.cpp`) | The four-round SAT baseline and its semantic regression boundary |
| [BAKSHEESH reference implementation](https://github.com/anubhab001/baksheesh) | Cipher, bit ordering and test vectors for the planned benchmark |
| Supplementary material for *Accelerating the Search…* | Legacy CaDiCaL-based search baseline |
| CRAFT and WARP supplementary material | Source and pattern inventory for the deferred portability work |
| [CryptoMiniSat](https://github.com/msoos/cryptominisat) 5.14.7 | The exact solver behind every verified result |

## Reproduction scope

The toolchain reproduces a bounded part of the published GIFT-64 analysis and
says so explicitly. Some artifacts needed for a full paper-scale reproduction —
notably the original stage-4 key candidate corpus, the trail-selection
provenance, and the generators behind the coexistence matrix and the 18/19-round
extensions — are not present in the public archives. Where that is the case, the
affected stage is marked `blocked` in
[project status](current_analysis/project_status.md) rather than approximated.

Runtime figures reported in the source papers were measured on different
hardware and solver versions and are not comparable with anything measured here.
