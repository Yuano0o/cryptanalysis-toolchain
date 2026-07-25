# Repository–Paper–Module Map

This is the concise source-of-truth map for the project. Paths are relative to
this repository. Upstream repositories are read-only and retain independent Git
histories.

| Paper or supplementary material | Local file | Upstream repository / relevant code | Research module | Implementation status / TODO |
|---|---|---|---|---|
| *Accelerating the Search of Differential and Linear Characteristics with the SAT Method* | `../papers/accelerating-search/01_accelerating_search_differential_linear_sat.pdf` | `../upstream/Accelerating_Automatic_Search/1.Source-Code/`; PRESENT, LBlock, and SIMON `SearchWithCadical.py` scripts | Exact SAT baseline, CNF generation, label generation, final verification | Partial public implementation found. CaDiCaL paths are hard-coded and CaDiCaL is not currently available. Paper ciphers beyond the three directories are not present. |
| *A Deeper Look at Related-Key Differentials of GIFT-64 from Trails to Differentials* | `../papers/gift64-differential/01_deeper_look_related_key_differentials_gift64.pdf` | `../upstream/Supplementary_Material_GIFT-64_Differential/Source_code/1...6`; trail/right-key-space supplementary PDFs and data | Main automated differential-level pipeline | Major stages are present but not end-to-end reproducible. Stage 4 expects missing `KeyCandidate.out`; 18/19-round extension generation code was not identified. |
| *A Linearisation Method for Identifying Dependencies in Differential Characteristics: examining the intersection of deterministic linear relations and nonlinear constraints* | `../papers/gift64-differential/02_linearisation_method_differential_dependencies.pdf` | GIFT repository stages 2–5: LC, LNC, fixed-key testing, remaining-probability testing | Constraint analysis and probability evaluation | Paper found, reviewed, and archived with the GIFT material. Strong conceptual/code correspondence found; TODO: confirm exact script-version-to-section provenance with the author. |
| *More Accurate Differential Properties of LED64 and Midori64* | `../papers/gift64-differential/03_more_accurate_differential_properties_led64_midori64.pdf` | No direct LED64/Midori64 repository in this workspace; GIFT stage 6 applies related coexistence/Max-PoSSo ideas | Method reference for right-pair/weak-key/coexistence analysis | Methodology found; complete cipher-specific implementation not found. |
| *Investigation of the Optimal Linear Characteristics of BAKSHEESH* | `../papers/baksheesh/01_optimal_linear_characteristics_baksheesh.pdf` | `../upstream/Supplementary_Material_BAKSHEESH/main.cpp` | Initial benchmark, cipher adapter, later SAT/ML experiments | Encryption implementation and test vector found; optimal-characteristic SAT search and enumeration code not found. TODO: ask whether the original search code is available. |
| *NeuroGIFT: Using a Machine Learning Based SAT Solver for Cryptanalysis* | `../papers/ml-guided-sat/01_neurogift_ml_sat_cryptanalysis.pdf` | No implementation, dataset, or model found in the four local repositories | ML-guided SAT task definition; GIFT CNF classification/ranking reference | Paper found; code/data/model availability is TODO. Treat predictions only as guidance for an exact solver. |
| *Learning a SAT Solver from Single-Bit Supervision* (NeuroSAT) | `../papers/ml-guided-sat/02_neurosat_single_bit_supervision.pdf` | No NeuroSAT repository vendored locally | Literal–clause graph and message-passing baseline | Paper found; implementation not present. TODO: select a maintained external reference only if dependency work is later approved. |
| *Key-Recovery Attacks on CRAFT and WARP* | Main paper PDF not found locally; supplementary files are under `../papers/craft-warp/` | `../upstream/CRAFT-and-WARP/`; staged C++ programs are packaged in `3.CRAFT-Source-Code.zip` and `5.WARP-Source-Code.zip` | Later portability evaluation | Title confirmed from `ReadMe.pdf`; source stages syntax-check, but no end-to-end run was attempted. TODO: obtain the paper and establish pattern–stage–result provenance. |

## Upstream repository roles

- `Accelerating_Automatic_Search`: exact SAT reference and potential dataset
  generator.
- `Supplementary_Material_GIFT-64_Differential`: primary pipeline reference.
- `Supplementary_Material_BAKSHEESH`: initial cipher implementation benchmark,
  not a complete search framework.
- `CRAFT-and-WARP`: later cross-cipher portability material.

BAKSHEESH, GIFT-64, CRAFT, and WARP are experimental objects, not four separate
research directions.
