# 项目总览

> 扫描基线：2026-07-25。本文档描述当前本地工作区可验证的内容，不代表尚未公开的研究结论。

## 项目目的

本项目的目标，是把多篇论文中分散的自动搜索、trail dependency、fixed-key
validation、概率评估和 trail coexistence 方法，整理成一个可复现、可扩展、可测试的
**differential-level analysis framework**。

框架不以机器学习替代密码学验证。机器学习只负责缩小搜索范围、改善候选顺序或预测
求解难度；任何最终 trail、constraint、right-key space、概率或 coexistence 结论，都
必须由精确 SAT solver 或等价的精确方法验证。

工作区分为三个信任边界：

- `../upstream/`：四个公开参考仓库，保留独立 Git 历史，只读；
- `../papers/`：论文和补充 PDF，不进入研究 Git 仓库；
- 当前 `learning-guided-cryptanalysis/`：Learning-Guided Cryptanalysis 的 private Git
  repository，保存自己的 adapters、pipeline、测试、配置、实验入口和研究文档。

## 两条研究主线

### 主线 A：Automated Differential-Level Analysis Pipeline

主线 A 是精确分析平台。目标是把当前 GIFT-64 仓库中的脚本式流程重构为可组合阶段：

1. 搜索同一 differential 下的 dominant/minor trails；
2. 提取 linear constraints（LC）；
3. 提取 linearised nonlinear constraints（LNC）；
4. 在候选 right-key space 上执行 fixed-key validation；
5. 估计 remaining probability；
6. 分析多条 trail 是否可共存，以及合并后 differential 的有效概率；
7. 将 8.25-round self-cancelling core 扩展到 18/19-round differential。

当前公开代码已经覆盖上述流程的多个核心计算步骤，但仍是六个独立 C++ 程序：
参数、文件名和阶段连接大多硬编码，缺少统一构建、数据 schema、运行 manifest、
deterministic seed、端到端测试和错误检查。18/19-round extension 也未发现独立的自动化
入口。

### 主线 B：ML-Guided SAT Search

主线 B 是主线 A 和其他 SAT 搜索的辅助模块，目标包括：

- partial trail scoring；
- candidate ranking；
- branch/decision prioritisation；
- solver runtime 或 difficulty prediction；
- 优先选择值得交给精确 solver 的候选；
- 从精确 solver 生成带可审计 provenance 的训练标签。

NeuroGIFT 证明了 specialised SAT classification 在结构化 GIFT 实例上可以优于原始
NeuroSAT 的通用训练方式，但论文也明确指出：模型可能利用 input/output difference 的
表面结构；无法稳定提取 satisfying assignment；图规模带来显存瓶颈；输出只是近似
confidence。因此本项目不把“SAT/UNSAT 分类器”直接视为密码学求解器，而把它定位为
精确搜索前端的 ranking/guidance 组件。

## benchmark 与迁移关系

### BAKSHEESH：第一阶段 benchmark

BAKSHEESH 是最适合先建立测试闭环的对象：

- 本地公开仓库只有 175 行 C++ 加密实现，边界清楚；
- S-box、轮常数、置换、密钥编排和 35 轮加密均可直接识别；
- 代码可在当前机器用标准 C++11 编译并运行；
- 对应论文给出最优线性特征的理论结构和计数结果；
- 但公开仓库未包含论文使用的 SAT 最优特征搜索代码。

因此，BAKSHEESH 适合作为“从 cipher implementation 到测试向量、SAT encoding、精确
baseline、候选 ranking”的第一个完整重建案例，而不是把现有仓库误当成搜索实现。

### GIFT-64：主要复杂应用

GIFT-64 是主要的 differential-level 场景。它同时包含：

- trail enumeration；
- LC/LNC；
- right-key space；
- fixed-key SAT validation；
- simulated statistical testing；
- Max-PoSSo-style coexistence；
- differential extension。

完成 BAKSHEESH 的小型端到端闭环后，再把相同的配置、artifact schema、solver adapter、
测试与 provenance 机制应用到 GIFT-64，可降低一次性重构六阶段代码的风险。

### CRAFT/WARP：第二阶段迁移验证

CRAFT/WARP 仓库的 README 明确说明它是论文
**Key-Recovery Attacks on CRAFT and WARP** 的补充材料。仓库包含 CRAFT/WARP 的
related-key/related-tweak-key differential patterns、WARP zero-correlation linear
approximations，以及分阶段 key-recovery C++ 代码。

它们不是当前 pipeline 的直接实现，但适合作为后续 portability benchmark，检验：

- cipher abstraction 是否过度依赖 GIFT/BAKSHEESH 的 SPN 表达；
- trail、key dependency 和候选 artifact schema 是否可迁移；
- ML guidance 是否学习了通用搜索信号，还是仅记住某一密码的 CNF 拓扑。

## 建议阶段

| 阶段 | 目标 | 精确验证 |
|---|---|---|
| 0. Reproducibility contract | 固定数据 schema、solver adapter、manifest、seed、日志边界 | 小型 deterministic fixtures |
| 1. BAKSHEESH baseline | 重建线性 trail SAT 搜索并验证已知 bounds/结构 | 精确 SAT + 加密测试向量 |
| 2. GIFT pipeline extraction | 包装六个公开阶段，消除手工文件传递 | 与公开输入/表格/约束结果比对 |
| 3. ML guidance | 训练 ranking/difficulty 模型，不负责最终判定 | 所有候选回交精确 solver |
| 4. Portability | CRAFT/WARP 适配与跨密码实验 | 独立 cipher fixtures 和精确搜索 |
| 5. Public contribution review | 识别可独立上游化的小修复 | 全新公开分支、最小 diff、无私有历史 |

## 当前边界

- 四个 upstream 工作树均为干净的 `main`；本次扫描未修改上游。
- 当前机器未发现 CaDiCaL 可执行文件或 CryptoMiniSat 5 头文件/库。
- 不安装依赖，不运行长时间搜索，不生成或提交 CNF、日志、模型、数据和实验输出。
- `learning-guided-cryptanalysis/` 尚无 framework implementation；当前内容主要是结构和文档。
- Linearisation 论文已归档为
  `../papers/gift64-differential/02_linearisation_method_differential_dependencies.pdf`。
- 当前没有本地 NeuroGIFT/NeuroSAT 实现、训练集或模型权重。
- 不建立 fork、不准备 PR、不推送 GitHub。

## 未解决问题

最重要的未知项是：

1. BAKSHEESH 论文使用的 SAT 搜索源码是否可获得；
2. NeuroGIFT 的模型代码、数据生成器、训练样本和 checkpoint 是否可获得；
3. GIFT 六个程序与两篇最新论文每个表格/章节的精确对应关系；
4. 缺失的 `KeyCandidate.out` 应如何生成，以及公开参数是否足以复现；
5. 哪些 GIFT 阶段可抽象为通用模块，哪些必须保留 cipher-specific semantics；
6. CRAFT/WARP 分阶段代码的完整运行顺序、预期中间结果和可接受 runtime；
7. 哪些小型改动将来适合以全新公开提交贡献给上游。

详细跟踪见 [open_questions.md](open_questions.md)。
