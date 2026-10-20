# Phase 1: Foundation & Quality - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-01
**Phase:** 01-foundation-quality
**Areas discussed:** CI workflow 结构, lint 检查落地机制, golden-file 基线, log 级别/进度可见性

> Context: SPEC.md (`01-SPEC.md`) had already locked WHAT (4 requirements), boundaries, acceptance criteria, verification mechanisms, CI matrix, and trigger conditions via a prior `/gsd-spec-phase` run (ambiguity 0.16). This discussion resolved only the HOW (implementation decisions).

---

## CI Workflow 结构

| Option | Description | Selected |
|--------|-------------|----------|
| 单个新文件 ci.yml | 一处管 fmt/clippy/test/wheel-build；与 docs.yml / performance-regression.yml 并列 | ✓ |
| 拆 rust-ci.yml + wheel.yml | Rust 门控与 wheel 构建分离，触发条件可调 | |
| 合并进 performance-regression.yml | 复用其 cache/matrix；但职责混淆 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 独立 job 矩阵并行 | fmt 快速失败、clippy/test/build 并行；失败定位快 | ✓ |
| 单 job 多 step 串行 | cache 复用最充分；但一步挂住阻塞后续 | |
| 快/慢两档 job | fmt+clippy 快 job，test+build 慢 job | |

| Option | Description | Selected |
|--------|-------------|----------|
| 独立 job：cd pyo3 && cargo clippy | 与 wheel-build 合并；pyo3/Cargo.toml 独立门控 | ✓ |
| 主 job 额外 step | 复用主 job 环境；需 -manifest-path | |
| 同 job -manifest-path pyo3 | 一个 job 覆盖两 crate clippy | |

| Option | Description | Selected |
|--------|-------------|----------|
| 任一矩阵 job 失败即 PR 失败 | 符合 P1；分支保护要求所有检查通过 | ✓ |
| clippy 仅 ubuntu 跑，macOS 跑 test+build | clippy 平台无关；但 macOS 漏告警 | |
| 仅 ubuntu 必绿，macOS 非阻塞 | 违背矩阵初衷与双平台声明 | |

**User's choice:** ci.yml 单文件 · 独立 job 矩阵并行 · pyo3 独立 job · 任一 job 失败即 PR 失败
**Notes:** All recommended options. Mirrors `performance-regression.yml` cargo-cache pattern.

---

## lint 检查落地机制

| Option | Description | Selected |
|--------|-------------|----------|
| crate 级 #![deny] + CI 兑底 | src/lib.rs #![deny]，本地即报；CI 兑底 | |
| 仅 CI：cargo clippy -- -D ... | 本地不阻开发；但本地可能漏改 | |
| 两者都要（本地 + CI 双保险） | src/lib.rs #![deny] + CI 显式 -D 双保险 | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| src/cli/mod.rs 顶部 #![allow(...)] | 整个 cli 子树一次 allow | ✓ |
| 每个 println! 处 #[allow] 逐个标 | 最细粒度；维护负担大 | |
| deny 仅限 src/lib.rs，cli 自然不受约束 | 依赖模块边界；main.rs/pyo3 需另处理 | |

| Option | Description | Selected |
|--------|-------------|----------|
| syn 解析 string literal 查 CJK | 精确区分字面量/注释；新增 syn dev-dep | ✓ |
| CI 脚本先剥注释再 grep CJK | 零新依赖；但剥注释 edge case 易误判 | |
| 自定义 dylint / clippy-lint | 最严；但实现成本超出 ROI | |

| Option | Description | Selected |
|--------|-------------|----------|
| cargo test 的 #[test]，本地+CI 都跑 | 与 clippy deny 一致；syn 方案契合 | ✓ |
| 仅 CI 专用 step（脚本） | 本地不跑；配合脚本方案 | |
| pre-commit hook 也加 | 提交前拦截；需 pre-commit 已安装 | |

**User's choice:** clippy deny 本地+CI 双保险 · allowlist 在 src/cli/mod.rs · CJK 用 syn 解析 string literal · 作为 cargo test #[test]
**Notes:** Strongest enforcement throughout. Adds `syn` as a dev-dependency.

---

## golden-file 基线

| Option | Description | Selected |
|--------|-------------|----------|
| 重构前现在捕获 golden .rkdb + sha256 commit | 最强证明字节不变；需 plan 第一步先捕获 | |
| 交叉一致：count-path vs RKDatabase::write_to_file | 无需预捕获；但略同义反复 | |
| 两者结合：golden 预捕获 + 交叉一致 | 最全 | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| commit 二进制 .rkdb 到 tests/fixtures/ + sha256 比对 | 二进制可读回；fixtures/ 有先例 | ✓ |
| 只 commit sha256 文本 | 仓库不存二进制；但无法读回样本 | |
| 测试内联小基线 | 最轻；代表性弱 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 用当前代码生成 legacy 样本 commit | 新 reader 读它验证向后兼容 | ✓ |
| 构造最小手写二进制 legacy 样本 | 精确控制 data_offset；但易错 | |
| 复用 golden .rkdb 兼作 legacy | 一物两用；需确认 data_offset=42 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 多输入矩阵：k=21/32/64、canonical on/off、sorted/unsorted | 覆盖常见路径 | ✓ |
| 单一代表性输入 | 最简；漏 k=64/unsorted 路径 | |
| 现有 tests/fixtures/*.fasta 全跑 | 复用 fasta；覆盖 k=33/48/64 | |

**User's choice:** golden 预捕获 + 交叉一致 · commit 二进制 .rkdb · legacy 样本由当前代码生成 · 多输入矩阵
**Notes:** Critical sequencing — plan must capture golden artifacts BEFORE refactoring `count.rs` (CONTEXT D-10).

---

## log 级别/进度可见性

| Option | Description | Selected |
|--------|-------------|----------|
| 进度走 info!，默认仍可见 | 保留 CLI UX；行为最小变化 | ✓ |
| 进度走 debug!，默认静默 | 合 CONCERNS 建议；但行为变化 | |
| 混合：里程碑 info!、细节 debug! | 折中 | |

| Option | Description | Selected |
|--------|-------------|----------|
| println!→info!，eprintln!→warn!/error!，dbg!→debug! | 保留信息量；eprintln 按语义细分 | ✓ |
| 全部 →debug!（除明确错误） | 默认最安静；可能丢信息 | |
| 逐处人工定级 | 最准；工作量最大（133 处） | |

| Option | Description | Selected |
|--------|-------------|----------|
| 复用现有 env，不加 flag | 最小改动；P2 锁定默认 info | ✓ |
| 新增 CLI -v/--verbose / -q/--quiet | 符合 CLI 习惯；但需改 clap/main | |
| 两者都支持（env + flag） | 最灵活；配置最复杂 | |

| Option | Description | Selected |
|--------|-------------|----------|
| env_logger 仅 CLI 初始化；pyo3 不初始化 | Python 侧零污染；合 FOUND-02 | ✓ |
| pyo3 桥接到 Python logging | Python 可见日志；越出 phase 范围 | |
| pyo3 也初始化 env_logger 到 stderr | 简单；但污染 Python stderr | |

**User's choice:** merge 进度走 info! 默认可见 · 标准映射 · 复用现有 env · pyo3 不初始化 logger
**Notes:** Preserves CLI UX; realizes FOUND-02's Python-embedding goal (zero stderr pollution).

---

## Claude's Discretion

- Concrete `timeout-minutes`, `concurrency`, cache-key versioning in `ci.yml` (follow `performance-regression.yml`).
- CJK `syn` test source-discovery method (hardcoded path list vs `walkdir`).
- Read-side `data_offset` removal: full removal vs one-line sanity assertion (legacy sample + golden sha256 must still pass).
- Splitting clippy/work across the 4 plans; only hard ordering is D-10 (capture golden first).

## Deferred Ideas

None — discussion stayed within phase scope. Adjacent CONCERNS.md tech debt explicitly out of scope per PROJECT.md.
