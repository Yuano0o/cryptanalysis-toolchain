# Upstream Repository Inventory

All paths are relative to `learning-guided-cryptanalysis/`. These repositories are read-only
references and retain independent Git histories.

| Repository | Path | Language / format | Main entry points | Intended use |
|---|---|---|---|---|
| Accelerating Automatic Search | `../upstream/Accelerating_Automatic_Search` | Python | `1.Source-Code/<cipher>/<task>/SearchWithCadical.py` for PRESENT, LBlock, and SIMON | Reference SAT encodings and CaDiCaL-driven search patterns; inform the common solver adapter and pipeline design. |
| GIFT-64 Differential Supplement | `../upstream/Supplementary_Material_GIFT-64_Differential` | C++ and data files | `Source_code/1.Searching_for_trails_contained_in_a_differential/main.cpp` through `Source_code/6.Checking_the_simultaneous_validity_of_trails/main.cpp` | Primary reference for automating the multi-stage GIFT-64 differential-level analysis pipeline. |
| BAKSHEESH Supplement | `../upstream/Supplementary_Material_BAKSHEESH` | C++ | `main.cpp` | Initial benchmark for cipher abstraction, SAT-search integration, and reproducibility tests. |
| CRAFT and WARP | `../upstream/CRAFT-and-WARP` | C++ and shell scripts packaged in source ZIPs | `3.CRAFT-Source-Code.zip` and `5.WARP-Source-Code.zip`, each containing staged `main.cpp` programs | Secondary reference for staged key-recovery/differential workflows and future cross-cipher validation. |

## Verified upstream state

| Repository | Official remote | Local branch | Verified commit |
|---|---|---|---|
| Accelerating Automatic Search | `https://github.com/SunLing134340/Accelerating_Automatic_Search.git` | `main` | `9c96d414402819c8b7ee3ed0b755bd73fb9d00e7` |
| GIFT-64 Differential Supplement | `https://github.com/SunLing134340/Supplementary_Material_GIFT-64_Differential.git` | `main` | `5de31d9153347e56c7c9260c070384bfeb7feb60` |
| BAKSHEESH Supplement | `https://github.com/SunLing134340/Supplementary_Material_BAKSHEESH.git` | `main` | `3c06cdb1379f656e72cc5b80a717a72790fb37f3` |
| CRAFT and WARP | `https://github.com/SunLing134340/CRAFT-and-WARP.git` | `main` | `55808b628f286b7995e8cfd427791c8366d68bf3` |

The original downloads were ZIP snapshots without `.git/`. Their recorded
archive commit IDs matched the official `main` heads where archive metadata was
available. The official histories were restored from the remotes, and the
resulting upstream work trees were verified clean.
