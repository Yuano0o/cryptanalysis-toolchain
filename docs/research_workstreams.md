# Research Workstreams

## 共同原则

四条 workstream 共享以下约束：

- upstream 只读，所有 wrapper 和新实现位于
  `learning-guided-cryptanalysis/`；
- ML 只排序或引导，最终结果由精确 solver 验证；
- 每个实验必须记录 cipher、rounds、objective、solver/version、seed、输入 hash 和
  expected validation；
- CNF、solver logs、模型权重、数据集和实验输出不提交 Git；
- 先建立小型、可重复、可测试的路径，再扩大轮数或数据规模。

## Workstream A：GIFT-64 differential-level pipeline

### 目标

把 `Supplementary_Material_GIFT-64_Differential/Source_code/` 的六个独立程序包装成
结构化 pipeline，同时保留与公开结果逐项对照的能力。

### 目标模块

| 模块 | 当前上游证据 | 研究仓库目标接口 |
|---|---|---|
| Trail search | `1.Searching_for_trails_contained_in_a_differential/main.cpp` | `TrailSearchRequest -> TrailSet` |
| LC extraction | `2.Finding_linear_constraints/main.cpp` | `Trail -> LinearConstraintSet` |
| LNC extraction | `3.Finding_linearized_nonlinear_constraints/main.cpp` | `Trail -> LinearisedNonlinearConstraintSet` |
| Stage 2 validation | `4.Stage2_test/main.cpp` | `(Trail, RightKeyCandidateSet) -> ConstraintAudit` |
| Stage 3 probability | `5.Stage3_test/main.cpp` | `(Trail, FixedKeys, SamplingPlan) -> ProbabilityEstimate` |
| Coexistence | `6.Checking_the_simultaneous_validity_of_trails/main.cpp` | `(TrailConstraintMatrix, objective) -> CompatibleTrailSet` |

### 第一批交付

1. 定义版本化的 trail、key-space、constraint 和 probability artifact schema；
2. 为每个上游阶段建立只读 adapter，不复制源代码；
3. 把硬编码参数提升为 research-side config；
4. 在 adapter 层验证输入文件存在、维度和 hash；
5. 保存可提交的 manifest 和 summary，不保存原始 solver 输出；
6. 为 Stage 2 缺失的 `KeyCandidate.out` 建立明确 blocker；
7. 用公开的 `TrailInformation.out` 和 `AllMatrix33Trail.out` 建立小型解析测试。

### 验收标准

- 相同公开输入得到可比较的 LC/LNC 或 compatible-trail 摘要；
- 每个阶段可单独运行、失败可诊断、artifact 可追踪来源；
- pipeline 不依赖手工复制同名 `.out` 文件；
- nondeterministic sampling 必须由 research-side seed/manifest 包装；
- 不声称复现 18/19-round 结果，除非逐项匹配论文表格和公开补充材料。

## Workstream B：ML-guided SAT

### 研究假设

结构化 cryptanalytic SAT 实例可能允许 specialised model 学到：

- 哪些 partial trail 更可能扩展为高质量完整 trail；
- 哪些候选更可能在给定 bound 下 SAT；
- 哪些实例或分支更可能导致较长 solver runtime；
- 哪些候选应优先交给精确 solver。

### 与 NeuroSAT/NeuroGIFT 的关系

NeuroSAT 使用 literal-clause graph：每个 literal 和 clause 是节点，出现关系构成
bipartite edges，互补 literals 另有连接；通过 message passing 更新 clause/literal
embeddings，并用单个 SAT/UNSAT bit 监督。

NeuroGIFT 保留这一表示，但把任务限制为 GIFT 最优 active-S-box characteristic：

- SAT 样本：固定 input/output difference 后，存在具有最优 active-S-box 数的 trail；
- UNSAT 样本：不存在满足该最优 bound 的对应 trail；
- 标签由 CryptoMiniSat 生成；
- 训练样本主要变化来自 rounds 与 input/output differences；
- V2 控制 SAT/UNSAT 对的非零 nibble 数，减少 Hamming-weight shortcut。

本项目不直接复刻“神经 SAT solver”结论，而优先研究更容易审计的辅助任务。

### 建议任务顺序

1. **Runtime prediction**：预测精确 solver 成本，不影响正确性；
2. **Candidate ranking**：对一批 partial trails 排序，全部候选仍可最终验证；
3. **Portfolio selection**：选择 solver/config 顺序；
4. **Branch prioritisation**：只作为 solver hint，保留完整回溯；
5. 最后才考虑 SAT/UNSAT classification 或 assignment decoding。

### 数据 contract

每条训练样本至少记录：

- cipher/version 与 rounds；
- CNF generator version 和 config hash；
- 变量/子句统计，不提交 CNF 本体；
- objective/bound；
- candidate/partial-trail 的结构化表示；
- exact solver、版本、退出状态、wall time、seed；
- 标签来源与验证状态；
- train/validation/test split 的 cipher/round separation。

### 关键风险与控制

| 风险 | 控制 |
|---|---|
| 模型利用 input/output Hamming weight shortcut | matched negatives、feature ablation、OOD rounds/ciphers |
| 图规模导致内存爆炸 | truncated/typed representation、局部子图、分层编码 |
| approximate confidence 被误作证明 | exact solver gate，报告 false-negative/false-positive |
| train/test CNF 模板泄漏 | 按 rounds、cipher family 或 generator version 分组切分 |
| runtime 标签受机器噪声影响 | 固定硬件、重复测量、censoring/timeout 标注 |

### 验收标准

- 在 exact success rate 不下降的前提下改善 time-to-first-validated-result；
- 至少报告 unguided SAT、heuristic baseline 和 learned guidance 三组对照；
- GIFT/BAKSHEESH 之外保留 CRAFT/WARP OOD 测试；
- 所有最终密码学结论可在关闭 ML 模块后独立验证。

## Workstream C：BAKSHEESH benchmark

### 目标

以最小对象建立第一个完整闭环：

`cipher model -> test vectors -> linear trail encoding -> exact SAT -> benchmark dataset -> ML ranking`

### 当前基础

- 上游 `main.cpp` 包含 S-box、35 个轮常数、128-bit permutation、key schedule 和加密；
- 固定 128-bit key/plaintext 写在 `main()` 中；
- 当前机器 C++11 编译和短时运行成功，输出
  `fc7e 61fe e3d5 8730 8ca7 bc59 4ebf 3244`；
- 论文指出该实现可通过设计者测试向量；
- 论文理论结果包括：`R >= 12` 时最优 absolute correlation 为
  `2^(-3R+2)`，最优 linear characteristics 数量为 3072。

### 缺口

公开仓库没有：

- SAT/CNF generator；
- optimal linear characteristic search；
- active-S-box bound 搜索；
- 3072 条 characteristics 的枚举器；
- 自动测试、构建文件和 CLI。

### 第一批交付

1. 在 research 中独立实现 cipher interface 和已知测试向量；
2. 建立 nibble/bit ordering 的显式转换测试；
3. 建立小轮数 linear propagation 与 SAT encoding；
4. 用 brute-forceable toy rounds 与精确 solver 双重验证；
5. 再验证论文中较长轮数的 active-S-box bounds；
6. 生成不含敏感结果的 benchmark manifest；
7. 训练最简单的 runtime/ranking baseline。

### 验收标准

- bit/nibble ordering 与上游和论文表述一致；
- 小轮数 exhaustive 结果与 SAT 一致；
- 长轮数结论不只依赖 ML；
- 所有 benchmark 标签包含 exact solver provenance。

## Workstream D：CRAFT/WARP portability evaluation

### 目标

测试 framework 和 guidance 是否超越 GIFT/BAKSHEESH 的特定结构。

### 当前基础

仓库 README 确认对应 **Key-Recovery Attacks on CRAFT and WARP**。两个 source ZIP
包含 Step0 至 Step7 的分阶段 C++ key-recovery 程序：

- CRAFT：49 个 hard-coded right pairs，多组 forward/backward partial-key tests；
- WARP：32 个 hard-coded right pairs，并附部分阶段候选 `.out` 文件；
- CRAFT Step5 的 `SetUpTest.sh` 会生成 16 个 case 目录并后台并行运行；
- 所有解压到临时目录的 `main.cpp` 已通过 C++11 syntax check，但未运行长任务。

### 迁移测试

1. cipher state/key/tweak abstraction 能否表达 CRAFT 和 WARP；
2. artifact schema 能否表示 related-tweak-key 和 GFN；
3. candidate ranking 是否需要新的 feature types；
4. GIFT 训练的 model 在 CRAFT/WARP 上是否退化；
5. cipher-agnostic guidance 与 cipher-specific guidance 的收益差异。

### 边界

当前仓库是 key-recovery supplementary material，不是完整 differential-level pipeline。
在确认论文步骤、候选文件来源和预期 runtime 前，不把 Step0-Step7 当成自动 benchmark
运行，也不把 pattern PDF 当作独立论文。

### 验收标准

- adapter 不修改或解包到 upstream 工作树；
- 至少一个 CRAFT 和一个 WARP 小型 fixture 可重复执行；
- portability 结论同时报告功能兼容性、性能和失败模式；
- 不因迁移测试而放宽 exact verification 原则。

## Workstream 依赖图

```text
Reproducibility contracts
    |
    +--> C: BAKSHEESH exact baseline
    |        |
    |        +--> B: first ranking/runtime models
    |
    +--> A: GIFT six-stage adapters
             |
             +--> B: GIFT guidance integration
                      |
                      +--> D: CRAFT/WARP portability
```
