# Feature Specification: RustKmer Python API Compatibility Verification

**Feature Branch**: `007-api-compatibility`
**Created**: 2025-12-02
**Status**: Draft
**Input**: User description: "验证rustkmer python api生成的 db 是否与rustkmer count 生成的是格式否一致能否互相支持；验证rustkmer 的 python api 是否能读取 rustkmer count 生成的 db 并能相互query 和fuzzy-query, 在 dev 分支基础上建立007分支执行。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Database Format Consistency Verification (Priority: P1)

A researcher needs to confirm that k-mer databases created using the RustKmer Python API have identical format and structure as those created using the Rust CLI count command, ensuring seamless interchangeability between Python and Rust workflows.

**Why this priority**: This is foundational for all cross-platform compatibility - without format consistency, no interoperability is possible.

**Independent Test**: Can be tested by creating equivalent databases using both Python API and Rust CLI with the same input data, then performing binary comparison and structural validation to verify identical format.

**Acceptance Scenarios**:

1. **Given** identical FASTA input files, **When** creating k-mer databases using both Python API and Rust CLI with same parameters (k-mer size, counting method), **Then** both databases must have identical binary structure and metadata
2. **Given** a database created with Python API, **When** examining its file format and structure, **Then** it must match the specification used by Rust CLI databases exactly
3. **Given** databases created by both methods, **When** performing direct file comparison, **Then** all structural elements, headers, and data organization must be identical

---

### User Story 2 - Cross-Platform Query Interoperability (Priority: P1)

A bioinformatician needs to query k-mer databases created by the Rust CLI using the Python API, and vice versa, enabling flexible workflow integration between Python analysis pipelines and Rust processing tools.

**Why this priority**: This enables practical interoperability - users can choose the best tool for each step in their workflow without being locked into one ecosystem.

**Independent Test**: Can be tested by creating databases with one tool (Rust CLI) and querying them with the other (Python API), then verifying identical results when compared to querying with the same tool that created the database.

**Acceptance Scenarios**:

1. **Given** a k-mer database created with Rust CLI count command, **When** querying for specific k-mers using Python API, **Then** results must exactly match querying the same database with Rust CLI query command
2. **Given** a k-mer database created with Python API, **When** querying for specific k-mers using Rust CLI, **Then** results must exactly match querying the same database with Python API
3. **Given** both tools querying the same database, **When** comparing query results for identical k-mer sets, **Then** counts, metadata, and any additional information must be 100% identical

---

### User Story 3 - Fuzzy Query Cross-Platform Support (Priority: P2)

A genomics researcher needs to perform fuzzy k-mer searches with wildcard characters and mutation tolerance across both Python API and Rust CLI, ensuring that advanced query capabilities work consistently regardless of which tool created or queries the database.

**Why this priority**: Fuzzy querying is an advanced feature that provides significant value for real-world genomics applications where sequence variations and uncertainties are common.

**Independent Test**: Can be tested by performing equivalent fuzzy queries (wildcards, mutation tolerance) using both tools on databases created by either method, then validating identical result sets and match criteria.

**Acceptance Scenarios**:

1. **Given** any k-mer database (created by Python API or Rust CLI), **When** performing fuzzy queries with wildcards using Python API, **Then** results must match equivalent fuzzy queries performed with Rust CLI
2. **Given** fuzzy queries with mutation tolerance, **When** executing these queries on the same database using both tools, **Then** match criteria, distance calculations, and result sets must be identical
3. **Given** complex fuzzy query patterns (multiple wildcards, specific constraints), **When** running these patterns through both tools, **Then** all results must match with identical scoring and filtering

---

## Clarifications

### Session 2025-12-02

- Q: 测试数据规模和性能基线如何定义？ → A: 小型(1MB-100MB)、中型(100MB-10GB)、大型(>10GB)，跨平台操作性能开销<10%
- Q: 模糊查询的范围和复杂度如何界定？ → A: 支持基础模糊功能：单/双通配符(N)、1-2个突变距离、简单组合查询
- Q: 版本兼容性策略是什么？ → A: 渐进兼容：支持相邻主版本，提供版本转换工具和兼容性检查器
- Q: 错误处理和验证深度如何设置？ → A: 混合策略：元数据严格验证，数据内容容错，多层错误处理机制
- Q: 测试覆盖的优先级如何分配？ → A: 重点：格式一致性(40%) + 查询准确性(30%) + 模糊功能(20%) + 边界情况(10%)
- Q: 兼容性优先级和权威基准如何确定？ → A: 严格从属：Python API必须100%兼容Rust CLI格式，不允许任何Python特有功能或差异
- Q: Python绑定层的统一性如何实现？ → A: 完全统一：Python API和Rust CLI必须调用相同的底层Rust函数，只是接口层不同
- Q: 修改权限和优先级策略如何确定？ → A: 极其保守：只有当Python API无法通过绑定层实现CLI功能时才修改CLI代码
- Q: 数据库格式统一策略如何确定？ → A: 强制Python API使用Rust CLI的二进制格式(.rkdb文件)，确保真正的格式一致性

### Edge Cases

- CLI代码保守原则：Rust CLI代码修改必须极其保守，只有Python API无法通过绑定层实现时才修改
- 绑定层优先：优先通过改进Python绑定层来实现兼容性，避免修改CLI核心代码
- 共享核心函数验证：Python API和Rust CLI必须调用相同的底层Rust函数，确保行为完全一致
- 必要修改界定：只有当无法通过PyO3绑定层暴露CLI功能时，才考虑修改CLI代码
- 修改影响评估：任何CLI代码修改必须评估对现有功能的影响，确保向后兼容性

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Python API MUST generate k-mer databases as single binary .rkdb files, identical in format to Rust CLI databases, with no directory structures or Python-specific variations
- **FR-002**: Python API MUST successfully read and query single .rkdb files created by Rust CLI count command with 100% compatibility
- **FR-003**: Python API MUST NOT use directory-based storage or introduce any format variations that deviate from Rust CLI .rkdb file specification
- **FR-011**: Python API and Rust CLI MUST use identical underlying Rust functions, with only interface layer differences between languages
- **FR-012**: Rust CLI code modifications MUST be extremely conservative, only when Python API cannot achieve CLI functionality through binding layer
- **FR-004**: Query results MUST be identical across both tools when querying the same database, with Python API results matching Rust CLI exactly
- **FR-005**: Fuzzy query functionality MUST work consistently across both tools, following Rust CLI implementation as the reference
- **FR-006**: Python API MUST handle single .rkdb database files exactly as defined by Rust CLI specification, generating and reading identical binary files
- **FR-007**: Database creation parameters MUST match Rust CLI behavior precisely, with no Python-specific variations
- **FR-008**: Version compatibility MUST prioritize Rust CLI versions, with Python API adapting to Rust CLI changes
- **FR-009**: Error handling MUST align with Rust CLI behavior while maintaining Python-specific interface requirements
- **FR-010**: Cross-platform operations MUST maintain performance overhead under 10% compared to native Rust CLI operations

### Key Entities *(include if feature involves data)*

- **K-mer Database**: Single binary .rkdb file following Rust CLI specification exactly, containing k-mer sequences and metadata, supporting size categories: small (1MB-100MB), medium (100MB-10GB), large (>10GB). Python API must generate and read identical .rkdb file format, not directory structures
- **Rust CLI Reference Standard**: Authoritative database format and behavior definition that Python API must follow precisely
- **Query Interface**: Python API wrapper that provides identical query behavior to Rust CLI, including exact match, wildcard, and fuzzy search capabilities
- **Database Metadata**: Header information exactly matching Rust CLI format, containing k-mer size, creation parameters, version information, and indexing details
- **Query Result**: Results that exactly match Rust CLI output format, including k-mers, counts, and metadata
- **Shared Rust Core**: Common Rust functions used by both CLI and Python bindings, ensuring unified behavior
- **Interface Layer**: Python-specific wrapper (PyO3 bindings) around shared Rust core functions
- **CLI Layer**: Command-line interface wrapper around shared Rust core functions
- **Validation System**: Mechanisms to verify Python API compliance with Rust CLI standards

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Python API databases must be bit-for-bit identical to Rust CLI databases when using identical input data and parameters
- **SC-002**: Python API query results must exactly match Rust CLI results (100% accuracy) on any database created by Rust CLI
- **SC-003**: Fuzzy query results must be 100% identical between Python API and Rust CLI for all supported query patterns
- **SC-004**: Python API performance overhead is under 10% compared to native Rust CLI operations across all database sizes
- **SC-005**: Testing validates Python API as a strict superset of Rust CLI compatibility - Python API can do everything Rust CLI can do, identically
- **SC-006**: No Python-specific format variations or behavioral deviations from Rust CLI specification
- **SC-007**: All edge cases and error conditions in Python API produce identical behavior to Rust CLI
- **SC-008**: Python API and CLI use identical underlying Rust functions, verified through shared codebase analysis
- **SC-009**: Rust CLI modifications minimized and only made when absolutely necessary for Python API binding compatibility