# Feature Specification: Python Binding API for rustkmer

**Feature Branch**: `001-python-binding`
**Created**: 2025-01-13
**Status**: Draft
**Input**: User description: "开发rustkmer 的 python binding api, 从query开始，  注意需要使用真实数据进行CLI和API的一致性检查。真实数据 /Users/forrest/Data/data/kmer/K19/R1_001.rkdb ，测试dump的前  1000条数据。不要使用pyo3。"

## Clarifications

### Session 2025-01-13

- Q: 技术实现方案 - 如何在不使用 PyO3 的情况下实现 Python 与 Rust 代码的交互？ → A: 使用 subprocess 调用 CLI 命令并解析输出
- Q: 性能基准测试环境 - 使用什么数据库作为性能测试的标准？ → A: 使用指定的真实数据库文件 /Users/forrest/Data/data/kmer/K19/R1_001.rkdb
- Q: 错误处理策略 - 如何处理 API 中的错误情况？ → A: 使用 Python 标准异常（IOError、ValueError 等）进行错误处理
- Q: Python API 设计风格 - 采用什么样的接口设计模式？ → A: 面向对象设计（Database 类包含各种方法）
- Q: 批量查询支持 - 是否需要支持一次查询多个 k-mers？ → A: 提供批量查询方法，内部调用多次单个查询

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Python Query API (Priority: P1)

Python developers need to query k-mer databases programmatically without using PyO3, enabling integration with Python bioinformatics workflows.

**Why this priority**: Core functionality required for all Python-based bioinformatics tools that need to access rustkmer databases

**Independent Test**: Can be fully tested by performing queries on the real database file and comparing results with CLI output for consistency

**Acceptance Scenarios**:

1. **Given** a Python environment with rustkmer bindings, **When** querying the test database with a specific k-mer, **Then** the API returns the exact same count as the CLI
2. **Given** the R1_001.rkdb database file, **When** dumping the first 1000 entries via Python API, **Then** the results match the CLI dump output exactly
3. **Given** invalid query parameters, **When** calling the Python query function, **Then** appropriate error messages are returned

---

### User Story 2 - Database Information Access (Priority: P2)

Researchers need to retrieve metadata about k-mer databases (k-mer size, total k-mers, etc.) through Python for analysis planning and validation.

**Why this priority**: Essential metadata access for proper data validation and workflow configuration

**Independent Test**: Can be tested by retrieving database stats and comparing with CLI stats output

**Acceptance Scenarios**:

1. **Given** a database file, **When** calling the Python API to get database information, **Then** k-mer size, total count, and other stats match CLI output
2. **Given** a non-existent database file, **When** attempting to access information, **Then** clear error messages are provided

---

### Edge Cases

- What happens when the database file is corrupted or inaccessible?
- How does the API handle very large k-mer query result sets?
- Memory management when querying thousands of k-mers in sequence

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Python API MUST provide query functionality that accepts k-mer sequences and returns exact counts
- **FR-002**: Python API MUST support database dump functionality to retrieve k-mer entries
- **FR-003**: Python API MUST provide database metadata access (k-mer size, total entries, etc.)
- **FR-004**: Python API MUST handle error conditions gracefully with informative messages using Python standard exceptions
- **FR-005**: Python API MUST NOT use PyO3 as specified constraint
- **FR-006**: Python API MUST produce identical results to CLI commands when tested with the same data (see also SC-001)
- **FR-007**: Python API MUST be implemented using subprocess to call CLI commands
- **FR-008**: Python API MUST use object-oriented design with a Database class containing methods
- **FR-009**: Python API MUST support batch query functionality by internally calling multiple single queries

### Key Entities *(include if feature involves data)*

- **K-mer Database**: Binary database file (.rkdb format) containing k-mer counts and metadata
- **Query Result**: K-mer sequence and its associated count from the database
- **Database Metadata**: Information about k-mer size, total entries, file format version

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Python API query results match CLI output with 100% accuracy when tested against /Users/forrest/Data/data/kmer/K19/R1_001.rkdb
- **SC-002**: Database dump of first 1000 entries from R1_001.rkdb completes in under 5 seconds
- **SC-003**: Memory usage stays below 500MB when querying large databases
- **SC-004**: API installation works with standard pip install without requiring Rust compilation by end users
