# Open Questions

> 状态说明：`阻塞` 表示缺失信息会阻止可复现运行；`待确认` 表示当前有合理映射，但本地
> 证据不足以作最终结论；`设计决策` 表示需要项目内部选择。

## 优先问题

| 优先级 | 问题 | 当前证据 | 状态 | 建议下一步 |
|---|---|---|---|---|
| P0 | BAKSHEESH 原始最优线性特征搜索代码是否存在？ | 论文称使用 [Accelerating SAT] 自动工具验证 23-35 轮 bounds 和 3072 条特征；公开 BAKSHEESH 仓库只有加密 `main.cpp`。 | 阻塞 | 向论文作者确认搜索代码、参数和结果格式是否可共享；在此之前把搜索视为需要独立重建。 |
| P0 | NeuroGIFT 模型、数据生成器和训练数据是否可获得？ | 本地只有论文；工作区无仓库、数据、checkpoint。论文描述 CryptoMiniSat 标签生成和三种模型，但没有本地实现。 | 阻塞 | 确认 NeuroGIFT-V1/后续仓库状态、许可证、commit、数据 schema 与可共享范围。 |
| P0 | GIFT Stage 2 的 `KeyCandidate.out` 如何生成？ | README 说明 Stage 2 使用 1,000,000 个随机 keys；代码读取该文件，但仓库未包含。 | 阻塞 | 向上游确认生成算法、seed、文件 hash 和是否允许提供；不要自行假设与 Stage 3 的 1000-key 文件同分布即可复现。 |
| P0 | GIFT 六个程序与论文表格/章节的逐项对应关系是什么？ | 可从功能映射到 `A Deeper Look` Sec. 3-4 和 Linearisation Sec. 4-5，但代码无 section/table annotations。 | 待确认 | 建立“程序参数 -> 论文 figure/table -> expected output hash”核对表，并请作者确认。 |
| P1 | 哪些 GIFT 模块适合通用化？ | LC/LNC、SAT adapter、artifact parsing、fixed-key validation、probability runner 和 coexistence objective 看似可抽象；key schedule、state indexing、S-box affine spaces 属于 cipher-specific。 | 设计决策 | 先定义 protocol/interface，再用 GIFT 与一个 toy cipher 验证，避免直接抽取大段上游 C++。 |
| P1 | CRAFT/WARP 对应论文能否准确确认？ | 已由仓库 `ReadMe.pdf` 确认为 **Key-Recovery Attacks on CRAFT and WARP**；各 pattern PDF 是该论文补充材料。完整论文 PDF 当前不在工作区。 | 部分确认 | 获取并核对正式论文版本、章节、攻击参数和 source Step0-Step7 映射。 |
| P1 | 哪些内容适合以后向上游提交 PR？ | 当前可见候选包括 README 的缺失输入说明、portable build instructions、参数化路径、输入检查和 deterministic seed；尚未获公开许可。 | 待确认 | 先在 private adapters 中验证价值；获老师确认后，在全新 fork 分支重做最小独立改动。 |

## GIFT-64 pipeline 细节

### 1. `TrailInformation.out` 的正式 schema 是什么？

当前三个副本均为 543 行、2304 个 tokens、12063 bytes，但仓库没有 schema/version。
需要确认：

- 每个 group/trail 的记录边界；
- master-key difference 与每轮 `xin/xout` 的 bit/nibble ordering；
- 32 条 dominant trails 与输入文件中 `8 groups x 4 trails` 的精确顺序；
- stage 1 输出是否能 bit-for-bit 生成这些公开文件；
- minor trails 是否使用同一 schema。

### 2. Stage 1 是否覆盖论文全部枚举？

`ObjectiveProb=50`、`trailround=8`、`GroupIndex=0` 是编译期全局变量。代码一次只选择
一个 group；需要确认论文的 8 个 classes 是否通过手工修改 `GroupIndex` 分别运行，以及
31 条新增 optimal trails 的去重/分类步骤是否另有脚本。

### 3. LC/LNC 输出如何机器读取？

Stages 2 和 3 主要向 stdout 输出 LaTeX-like equations，没有结构化 artifact。
需要决定：

- 是解析 stdout，还是在 research 中独立实现相同线性代数；
- 如何保存 variable provenance；
- 如何验证 Gaussian elimination 的 basis/order 不同但空间等价；
- 32 个 right-key spaces 的 algebraic PDF 与程序输出如何逐项比对。

### 4. Stage 2 fixed-key test 的统计与复现参数

需要确认 1,000,000 keys 的生成方式、seed、是否从 initial right-key space 均匀抽样，
以及“不存在额外 constraints”的判定阈值。缺失 `KeyCandidate.out` 使当前公开代码无法
按 README 直接运行。

### 5. Stage 3 remaining probability 的 reproducibility

代码读取 `KeyCandidate1000.out`，并对每个 fixed key 使用 `std::random_device` 选择 21
个 input bits 和 values、重复 100 次。需要确认：

- 是否接受 nondeterministic reproduction；
- 如何注入显式 seed 而不修改 upstream；
- 论文中的 2^43 equivalent pairs 与代码统计之间的换算；
- 如何报告置信区间；
- 是否采用更有统计保证的 approximate model counting 作为对照。

### 6. Max-PoSSo/coexistence 输入从何生成？

Stage 6 读取 739 x 185 的 `AllMatrix33Trail.out`，代码内使用 58 个 trail indices。
需要确认：

- 矩阵如何从 LC/LNC 自动生成；
- “33”与论文中的 dominant/minor trail 集合如何对应；
- objective 是否寻找最大兼容 trail 数，还是枚举所有最大解；
- 是否存在从 minor trail search 到该矩阵的遗漏脚本。

### 7. 18/19-round extension 是否有公开实现？

当前仓库未发现专门生成 128 个 18-round 或 128 个候选 19-round differentials 的程序。
补充 PDF 给出 trails/spaces，但 extension、deduplication 与 key-recovery evaluation 可能
仍是手工或未公开流程。需要作者确认。

## ML-guided SAT

### 8. 首个 ML 任务应是什么？

候选：

- runtime/difficulty regression；
- partial-trail ranking；
- candidate SAT probability；
- branch prioritisation；
- solver portfolio selection。

建议先做 runtime prediction 和 ranking，因为它们不会改变 exact solver 的完备性。

### 9. 什么表示能避免 NeuroGIFT 的 graph-size 问题？

待比较：

- full literal-clause graph；
- objective-truncated graph；
- typed factor graph；
- round/S-box hierarchical graph；
- handcrafted structural features + lightweight ranker；
- solver-state features。

### 10. 如何避免 shortcut learning？

必须设计 matched negatives、Hamming-weight controls、round/cipher-disjoint splits、generator
version split 和 ablation。仅在相同 CNF 模板上随机切分 train/test 不足以证明泛化。

### 11. exact solver 如何接收 guidance？

需要选择不会破坏正确性的接口：

- candidate ordering；
- assumptions 顺序；
- phase/branch hints；
- solver portfolio；
- restart/timeout allocation。

任何 pruning 若可能漏解，必须有 fallback full search 或明确标注为 heuristic experiment。

## BAKSHEESH

### 12. bit/nibble ordering 的规范来源

论文指出设计者实现中在 bit permutation 前后存在 reverse nibble permutation，而补充实现
使用论文 Table 2 的 genuine permutation。需要把：

- designer representation；
- paper representation；
- upstream `main.cpp` representation；
- future SAT variable indexing

写成可测试转换，而不是在 adapter 中隐式处理。

### 13. “3072 optimal characteristics”如何成为测试 oracle？

需要确认完整特征列表是否存在、是否能从理论构造直接生成，以及相同 characteristic 在
旋转/对称下的 canonicalisation 规则。只有总数 3072 不能单独验证每条 SAT 输出。

## CRAFT/WARP

### 14. Step0-Step7 的正式运行顺序与候选文件 provenance

WARP ZIP 附带部分 `Step2Candidate1024.out`、`Step3Candidate4096.out`、
`KeyCandidate4096.out`、`Step5Candidate4.out`、`Step6Candidate4.out`；文件名与各阶段
读取关系并不完全按相邻步骤命名。CRAFT 多数候选直接硬编码或由独立 case 运行产生。
需要正式 manifest 说明每个输入由哪个参数化运行生成。

### 15. runtime 与资源需求

CRAFT Step5 的 shell 脚本会创建 16 个 case 并使用 `nohup` 并发运行。当前未执行。
在成为 benchmark 前，需要确认预计 CPU time、RAM、输出规模和终止条件。

## 未来上游贡献边界

可能适合公开 PR 的内容，仅限老师明确同意后重新实现：

- 修正 README 中 `KeyCandidate.out` 的缺失/生成说明；
- 增加非侵入式 build instructions；
- 增加输入文件存在性、维度与 parse error 检查；
- 将 hard-coded solver path 变为 CLI/config；
- 增加小型公开 test vector/smoke test；
- 增加 deterministic seed 选项，同时保留原默认行为。

不适合进入公开 PR：

- 私有 pipeline 历史；
- 内部架构文档和合作笔记；
- 失败实验；
- 未公开参数、结果或结论；
- ML 数据、模型、solver logs；
- 为私有研究临时复制的大规模上游改动。
