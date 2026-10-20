# Phase 2: Parallel Counting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-01
**Phase:** 02-parallel-counting
**Areas discussed:** 并行切分粒度, 并发计数结构, 线程配置 UX, 确定性与正确性

---

## 并行切分粒度

### Q1 — 主策略

| Option | Description | Selected |
|--------|-------------|----------|
| 文件内并行 | rayon 在单文件内跨 record 并行；CRR1936095 仅 2 part 下唯一能接近核心数加速的方案 | ✓ |
| 按文件并行 | 每文件一任务；最简但最多 ~2×，单大文件退化为单线程 | |
| 生产者-消费者 | 读+解压线程喂 channel，N worker 计数；解耦 I/O 但最复杂 | |

**User's choice:** 文件内并行
**Notes:** 选推荐项。后续两问基于此。

### Q2 — gzip 解压瓶颈

| Option | Description | Selected |
|--------|-------------|----------|
| 暂不动解压 | Phase 2 只并行解析+计数；Phase 4 实测；并行解压列 backlog | ✓ |
| 未同就并行化解压 | 按 gzip member 切分多线程 gunzip；普通 gzip 边界探测脆弱，风险高 | |

**User's choice:** 暂不动解压
**Notes:** 保持 Phase 2 聚焦、低风险。

### Q3 — 多文件汇合

| Option | Description | Selected |
|--------|-------------|----------|
| 全局记录池 | 所有文件 read 汇入一个并行计数 + 一个分片 map；打满核心 | ✓ |
| 两级并行(文件×记录) | 保留每文件边界；文件数<核心数时核心闲置 | |

**User's choice:** 全局记录池

---

## 并发计数结构

### Q1 — 并发计数结构

| Option | Description | Selected |
|--------|-------------|----------|
| dashmap | PCOUNT-02 点名；成熟；entry() 原子 upsert；新增依赖需过 clippy 闸门 | ✓ |
| 分片 hashbrown (无新依赖) | 自建分片 hashbrown+parking_lot+ahash；严格符合既有栈约束 | |
| per-thread 本地+reduce | 零锁最快；但人规模 ~N× 内存放大；仅适合小数据 | |

**User's choice:** dashmap
**Notes:** 接受新增依赖以换取成熟与低实现风险；API 保持不变。分片数/hasher/溢出语义/API 兼容为 Claude 裁量。

---

## 线程配置 UX

### Q1 — 默认线程数 + 配置范围

| Option | Description | Selected |
|--------|-------------|----------|
| 全部核心+全局池 | num_cpus + ThreadPoolBuilder::build_global()，count/merge 共享池 | ✓ |
| 全部核心+计数专用局部池 | 独立 ThreadPool，与 merge 隔离 | |
| 核心数-1 (留一空闲) | 与 PCOUNT-01 'all cores' 字面冲突 | |

**User's choice:** 全部核心+全局池

### Q2 — env 优先级

| Option | Description | Selected |
|--------|-------------|----------|
| --threads>RUSTKMER>RAYON | RUSTKMER_THREADS 优先，回退 RAYON_NUM_THREADS 保护既有用户 | ✓ |
| 忽略 RAYON_NUM_THREADS | 单一来源更干净，但既有用户需迁移 | |

**User's choice:** --threads>RUSTKMER>RAYON

### Q3 — Python 端线程控制

| Option | Description | Selected |
|--------|-------------|----------|
| PyCounter 暴露 threads | PyCounter(k,canonical,threads=None)；allow_threads 释放 GIL | ✓ |
| 只认 env 变量 | Python API 不加参数 | |

**User's choice:** PyCounter 暴露 threads

---

## 确定性与正确性

### Q1 — 默认排序

| Option | Description | Selected |
|--------|-------------|----------|
| 保持 --sort 可选 | 不改默认；PCOUNT-04 只要求 counts 一致 | |
| 默认排序 | --sort 默认 ON；--no-sort 关闭；保证可复现，对齐 Jellyfish2 | ✓ |

**User's choice:** 默认排序
**Notes:** 用户覆盖了"保持可选"的推荐。接受改变既有 CLI 默认 + 人规模排序开销；Phase 4 benchmark 实测，若 prohibitive 再评估 fast-path。已作为 flagged tradeoff 记入 CONTEXT D-09。

### Q2 — 正确性验证

| Option | Description | Selected |
|--------|-------------|----------|
| Golden-first+差分+proptest | 改前捕获基线；改后 1-vs-N 差分 + 基线一致 + proptest | ✓ |
| 仅 1-vs-N 差分 | 最轻量，但顺序路径自身 bug 抓不到 | |
| 仅 proptest | 缺真实数据基线/大输入覆盖 | |

**User's choice:** Golden-first+差分+proptest

---

## Claude's Discretion

- 并发结构：分片数/hasher 用 dashmap 默认；保留 u32 + u32::MAX 报错溢出语义；`KmerCounter` 内部字段换型、公共 API 不变。
- 线程配置：`--threads<1` 报错；verbose 报告线程数；`RAYON_NUM_THREADS` 仅在另两者未设时回退。
- 确定性：`should_sort = !no_sort`，保留 `--sort` 别名；既有 unsorted 字节比较测试改 set/sorted 比较；golden 覆盖 `k∈{21,32,64}`×canonical×多规模。
- 并行实现：bio 顺序 reader → 有界分块缓冲后 par_iter（非全量缓冲）；encode/canonicalize 在 worker 侧。

## Deferred Ideas

- 并行 gzip 解压（按 gzip member 边界多线程 gunzip）— Phase 4 benchmark 实测若被解压封顶再单列 phase。
- 自适应分片/前缀粒度的有界内存计数（MINIM-02/03 线）— v2 工作。
- 可配置计数器宽度/饱和告警（SAT-01/02）— v2；Phase 2 保留 u32。
