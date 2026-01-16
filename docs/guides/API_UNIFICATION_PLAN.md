# PyO3 与 Subprocess API 统一计划

**创建日期：** 2025年1月15日  
**目标：** 统一两个 Python 绑定的 API，以 PyO3 为准

---

## 一、差异分析

### 1.1 构造函数差异

| 组件 | Subprocess | PyO3 | 统一方案 |
|------|-----------|------|---------|
| Database | `Database(path, validate=False)` | `PyDatabase(path, load_mode)` | `Database(path, load_mode=None)` |
| FuzzyQuery | `FuzzyQuery(database)` | `PyFuzzyQuery(database)` | 统一为 `Database.fuzzy_query()` |
| PrefixQuery | 不存在 | `PyPrefixQuery(path)` | `Database.prefix_query()` |
| KmerCounter | `KmerCounter(k, canonical)` | `PyKmerCounter(k, canonical, capacity)` | `KmerCounter(k, canonical=True, capacity=None)` |

### 1.2 方法命名差异

| 功能 | Subprocess | PyO3 | 统一方案 |
|------|-----------|------|---------|
| 统计信息 | `stats()` | `get_stats()` | `stats()` |
| 单个查询 | `query(kmer)` | `query(kmer)` | `query(kmer)` |
| 批量查询 | `query_batch(kmers)` | `query_batch(kmers)` | `query_batch(kmers)` |
| 模糊查询 | `fuzzy_query(pattern, m)` | `fuzzy_query(pattern, mutations)` | `fuzzy_query(pattern, mutations=1)` |
| 前缀查询 | 不支持 | `query_prefix(prefix)` | `query_prefix(prefix)` |
| 混合查询 | 不支持 | `query_hybrid(pattern)` | `query_hybrid(pattern)` |

### 1.3 返回类型差异

| 类型 | Subprocess | PyO3 | 统一方案 |
|------|-----------|------|---------|
| QueryResult | dataclass: kmer, count, canonical | class: kmer, count, found | 统一为 dataclass |
| DatabaseStats | dataclass | class | 统一为 dataclass |
| FuzzyResult | class | class | 统一结构 |
| PrefixResult | dict | dict | 保持 dict |

### 1.4 异常差异

| Subprocess | PyO3 |
|-----------|------|
| DatabaseError | RustKmerError (PyErr) |
| QueryError | ValueError |
| InvalidKmerError | ValueError |
| SubprocessError | RuntimeError |

---

## 二、统一 API 设计

### 2.1 Database 类统一设计

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Iterator

class LoadMode(Enum):
    PRELOAD = "preload"      # 预加载到内存
    MEMORY_MAPPED = "mmap"   # 内存映射
    LAZY = "lazy"            # 延迟加载

@dataclass
class QueryResult:
    """统一查询结果"""
    kmer: str
    count: int
    canonical: Optional[str] = None
    found: bool = False

@dataclass  
class DatabaseStats:
    """统一数据库统计"""
    kmer_size: int
    total_kmers: int
    unique_kmers: int
    file_size: int
    is_sorted: bool
    is_canonical: bool

class Database:
    """
    RustKmer 数据库统一接口
    
    支持 Subprocess 和 PyO3 两种后端实现
    """
    
    def __init__(
        self, 
        path: str, 
        load_mode: Optional[LoadMode] = None,
        validate: bool = False
    ):
        """
        初始化数据库连接
        
        Args:
            path: 数据库文件路径
            load_mode: 加载模式 (PyO3 only, Subprocess 时忽略)
            validate: 是否验证数据库 (Subprocess only)
        """
        self._path = path
        self._load_mode = load_mode
        self._stats_cache: Optional[DatabaseStats] = None
    
    @property
    def path(self) -> str:
        """数据库路径"""
        return self._path
    
    @property
    def kmer_size(self) -> int:
        """K-mer 大小"""
        return self.stats().kmer_size
    
    @property
    def is_loaded(self) -> bool:
        """是否已加载"""
        return self._stats_cache is not None
    
    # ==================== 基础查询 ====================
    
    def query(self, kmer: str, validate: bool = True) -> QueryResult:
        """
        精确查询单个 k-mer
        
        Args:
            kmer: K-mer 序列
            validate: 是否验证 k-mer 格式
            
        Returns:
            QueryResult: 查询结果
            
        Raises:
            ValueError: kmer 无效
        """
        ...
    
    def query_batch(self, kmers: List[str], max_workers: int = 4) -> Dict[str, QueryResult]:
        """
        批量查询多个 k-mers
        
        Args:
            kmers: K-mer 列表
            max_workers: 最大并行数
            
        Returns:
            Dict[kmer, QueryResult]: 查询结果字典
        """
        ...
    
    # ==================== 统计信息 ====================
    
    def stats(self) -> DatabaseStats:
        """
        获取数据库统计信息
        
        Returns:
            DatabaseStats: 统计信息
        """
        ...
    
    # ==================== 高级查询 ====================
    
    def query_prefix(self, prefix: str) -> Dict[str, str]:
        """
        前缀查询
        
        Args:
            prefix: 前缀字符串
            
        Returns:
            Dict[kmer, count]: 匹配的结果
        """
        ...
    
    def query_fuzzy(
        self, 
        pattern: str, 
        mutations: int = 1,
        max_results: Optional[int] = None
    ) -> 'FuzzyResult':
        """
        模糊查询（支持通配符）
        
        Args:
            pattern: 模式 (支持 N 通配符)
            mutations: 最大突变数
            max_results: 最大结果数
            
        Returns:
            FuzzyResult: 模糊查询结果
        """
        ...
    
    def query_hybrid(self, pattern: str) -> Dict[str, str]:
        """
        混合搜索 (例如: ATGC{N5}TACG)
        
        Args:
            pattern: 混合模式
            
        Returns:
            Dict[kmer, count]: 匹配结果
        """
        ...
    
    # ==================== 数据库操作 ====================
    
    def dump(
        self, 
        limit: Optional[int] = None,
        offset: int = 0
    ) -> Iterator[QueryResult]:
        """
        导出数据库内容
        
        Args:
            limit: 最大导出数量
            offset: 起始偏移
            
        Yields:
            QueryResult: 查询结果
        """
        ...
    
    @staticmethod
    def merge(
        databases: List[str], 
        output: str,
        check_compatibility: bool = True
    ) -> None:
        """
        合并数据库
        
        Args:
            databases: 数据库路径列表
            output: 输出路径
            check_compatibility: 是否检查兼容性
        """
        ...
    
    # ==================== 上下文管理 ====================
    
    def __enter__(self) -> 'Database':
        """进入上下文"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出上下文"""
        ...
```

### 2.2 FuzzyResult 统一设计

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class FuzzyMatch:
    """模糊匹配结果"""
    kmer: str
    count: int
    distance: Optional[int] = None
    match_type: str = "exact"

@dataclass
class FuzzyResult:
    """模糊查询统一结果"""
    query: str
    exact_match: Optional[FuzzyMatch] = None
    matches: List[FuzzyMatch] = field(default_factory=list)
    total_matches: int = 0
    mutation_tolerance: int = 0
    has_position_mutations: bool = False
```

### 2.3 KmerCounter 统一设计

```python
from dataclasses import dataclass

@dataclass
class CounterStats:
    """计数器统计"""
    unique_kmers: int
    total_kmers: int
    kmer_size: int
    is_canonical: bool

class KmerCounter:
    """
    K-mer 计数器统一接口
    """
    
    def __init__(
        self, 
        kmer_size: int, 
        canonical: bool = True,
        capacity: Optional[int] = None
    ):
        """
        初始化计数器
        
        Args:
            kmer_size: K-mer 大小
            canonical: 是否使用规范形式
            capacity: 初始容量 (PyO3 only)
        """
        ...
    
    def add_sequence(self, sequence: str) -> None:
        """
        添加序列计数
        
        Args:
            sequence: DNA 序列
        """
        ...
    
    def add_kmer(self, kmer: str) -> None:
        """
        添加单个 k-mer
        
        Args:
            kmer: K-mer 序列
        """
        ...
    
    def get_stats(self) -> CounterStats:
        """
        获取统计信息
        
        Returns:
            CounterStats: 统计信息
        """
        ...
```

---

## 三、实现计划

### 阶段 1: 基础类型统一 (第 1 周)

#### 任务 1.1: 创建统一类型定义

**文件：** `python/rustkmer/types.py`

```python
# 统一的 QueryResult
@dataclass
class QueryResult:
    kmer: str
    count: int
    canonical: Optional[str] = None
    found: bool = False

# 统一的 DatabaseStats
@dataclass
class DatabaseStats:
    kmer_size: int
    total_kmers: int
    unique_kmers: int
    file_size: int
    is_sorted: bool
    is_canonical: bool

# 统一的 FuzzyResult
@dataclass
class FuzzyMatch:
    kmer: str
    count: int
    distance: Optional[int] = None
    match_type: str = "exact"

@dataclass
class FuzzyResult:
    query: str
    exact_match: Optional[FuzzyMatch] = None
    matches: List[FuzzyMatch] = field(default_factory=list)
    total_matches: int = 0

# 统一的异常
class RustKmerError(Exception):
    """基础异常"""
    pass

class DatabaseError(RustKmerError):
    """数据库错误"""
    pass

class QueryError(RustKmerError):
    """查询错误"""
    pass

class InvalidKmerError(RustKmerError, ValueError):
    """无效 K-mer"""
    pass
```

#### 任务 1.2: 更新 Subprocess 实现

**修改文件：**
- `python/rustkmer/database.py` - 使用统一类型
- `python/rustkmer/query.py` - 更新 QueryResult
- `python/rustkmer/stats.py` - 更新 DatabaseStats
- `python/rustkmer/fuzzy_query.py` - 更新 FuzzyResult
- `python/rustkmer/exceptions.py` - 统一异常层次

### 阶段 2: 方法签名统一 (第 2 周)

#### 任务 2.1: 统一 Database 方法

| 旧方法 (Subprocess) | 新方法 (统一) | 状态 |
|--------------------|--------------|------|
| `query(kmer, validate_strict)` | `query(kmer, validate)` | 重命名参数 |
| `stats()` | `stats()` | 保持 |
| `query_batch(kmers)` | `query_batch(kmers)` | 保持 |
| `fuzzy_query(pattern, m)` | `query_fuzzy(pattern, mutations)` | 重命名 |
| 不存在 | `query_prefix(prefix)` | 新增 |
| 不存在 | `query_hybrid(pattern)` | 新增 |
| `dump(limit, offset)` | `dump(limit, offset)` | 保持 |
| `merge(databases, output)` | `merge(databases, output)` | 保持 |

#### 任务 2.2: 统一 LoadMode

```python
# Subprocess 中添加
class LoadMode:
    PRELOAD = "preload"
    MEMORY_MAPPED = "mmap"  
    LAZY = "lazy"

# Database 构造函数更新
def __init__(
    self,
    path: str,
    load_mode: Optional[LoadMode] = None,
    validate: bool = False
):
    # load_mode 用于 PyO3 后端
    # validate 用于 Subprocess 后端
```

### 阶段 3: 后端统一 (第 3 周)

#### 任务 3.1: 创建后端抽象

```python
# python/rustkmer/backend.py

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Iterator

class DatabaseBackend(ABC):
    """数据库后端抽象"""
    
    @abstractmethod
    def query(self, kmer: str) -> QueryResult:
        ...
    
    @abstractmethod
    def query_batch(self, kmers: List[str]) -> Dict[str, QueryResult]:
        ...
    
    @abstractmethod
    def stats(self) -> DatabaseStats:
        ...

class SubprocessBackend(DatabaseBackend):
    """Subprocess 后端实现"""
    ...

class PyO3Backend(DatabaseBackend):
    """PyO3 后端实现"""
    ...
```

#### 任务 3.2: 实现自动后端选择

```python
# python/rustkmer/database.py

class Database:
    """统一数据库接口"""
    
    _backend: DatabaseBackend
    
    def __init__(self, path: str, load_mode=None, validate=False):
        # 尝试使用 PyO3 后端
        try:
            import rustkmer_pyo3
            self._backend = PyO3Backend(path, load_mode)
        except ImportError:
            # 回退到 Subprocess 后端
            self._backend = SubprocessBackend(path, validate)
    
    def query(self, kmer: str) -> QueryResult:
        return self._backend.query(kmer)
    
    # ... 其他方法委派给 backend
```

### 阶段 4: 完善 PyO3 功能 (第 4 周)

#### 任务 4.1: 添加缺失功能到 PyO3

**修改文件：** `pyo3/src/database.rs`

```rust
#[pymethods]
impl PyDatabase {
    // 现有方法...
    
    // 新增: dump 功能
    #[pyo3(signature = (limit, offset))]
    fn dump(&self, limit: Option<usize>, offset: usize) -> PyResult<Vec<PyQueryResult>> {
        // 实现导出功能
    }
    
    // 新增: merge 静态方法
    #[staticmethod]
    #[pyo3(signature = (databases, output))]
    fn merge(databases: Vec<String>, output: String, py: Python<'_>) -> PyResult<()> {
        // 实现合并功能
    }
    
    // 新增: create_from_counts 静态方法
    #[staticmethod]
    #[pyo3(signature = (kmer_size, counts))]
    fn create_from_counts(
        kmer_size: usize,
        counts: HashMap<String, u32>,
        py: Python<'_>
    ) -> PyResult<PySelf> {
        // 从计数创建数据库
    }
}
```

---

## 四、测试计划

### 4.1 创建统一测试套件

**文件结构：**
```
tests/
├── unit/
│   ├── test_types.py          # 测试统一类型
│   ├── test_database.py       # 测试 Database API
│   └── test_kmer_counter.py   # 测试 KmerCounter API
│
├── integration/
│   ├── test_subprocess_backend.py  # Subprocess 后端测试
│   ├── test_pyo3_backend.py        # PyO3 后端测试
│   └── test_backend_parity.py      # 后端一致性测试
│
└── contract/
    ├── test_api_contracts.py       # API 契约测试
    └── test_result_equivalence.py  # 结果等价性测试
```

### 4.2 测试用例模板

```python
# tests/integration/test_backend_parity.py

import pytest
from rustkmer import Database, KmerCounter
from rustkmer.types import QueryResult

class TestBackendParity:
    """测试两个后端的结果一致性"""
    
    @pytest.fixture
    def test_db_path(self):
        return "python/tests/test_data/tiny_test.rkdb"
    
    def test_query_result_parity(self, test_db_path):
        """测试查询结果一致性"""
        db = Database(test_db_path)
        
        # 测试多个 k-mers
        test_kmers = ["AAAAAAA", "CCCCCCC", "GGGGGGG", "TTTTTTT"]
        
        for kmer in test_kmers:
            result = db.query(kmer)
            
            # 验证结果结构
            assert isinstance(result, QueryResult)
            assert hasattr(result, 'kmer')
            assert hasattr(result, 'count')
            assert hasattr(result, 'found')
            assert result.kmer == kmer
    
    def test_stats_parity(self, test_db_path):
        """测试统计信息一致性"""
        db = Database(test_db_path)
        stats = db.stats()
        
        # 验证统计信息
        assert stats.kmer_size > 0
        assert stats.total_kmers >= stats.unique_kmers
        assert stats.total_kmers > 0
    
    def test_prefix_query_parity(self, test_db_path):
        """测试前缀查询一致性"""
        db = Database(test_db_path)
        
        result = db.query_prefix("AAA")
        
        # 验证返回类型和结构
        assert isinstance(result, dict)
        assert len(result) > 0
        
        # 验证值是字符串（count）
        for kmer, count in result.items():
            assert isinstance(kmer, str)
            assert kmer.startswith("AAA")
```

### 4.3 测试执行计划

```bash
# 阶段 1: 类型测试
pytest tests/unit/test_types.py -v

# 阶段 2: API 测试
pytest tests/integration/test_database.py -v

# 阶段 3: 后端一致性测试
pytest tests/integration/test_backend_parity.py -v

# 阶段 4: 完整测试
pytest tests/ -v --tb=short
```

---

## 五、修订 Pytest

### 5.1 更新 pytest 配置

**文件：** `python/pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = """
    -v
    --tb=short
    --no-cov
"""
markers = """
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks integration tests
    contract: marks contract tests
    parity: marks backend parity tests
    pyo3: marks PyO3 specific tests
    subprocess: marks Subprocess specific tests
"""

[tool.pytest.ini_options]
# 分开运行不同后端的测试
python_files = [
    "test_*.py",           # 通用测试
    "test_*_subprocess.py", # Subprocess 专用
    "test_*_pyo3.py",       # PyO3 专用
]
```

### 5.2 添加标记

```python
# tests/conftest.py

import pytest

def pytest_configure(config):
    """配置 pytest 标记"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow"
    )
    config.addinivalue_line(
        "markers", "integration: marks integration tests"
    )
    config.addinivalue_line(
        "markers", "contract: marks contract tests"
    )
    config.addinivalue_line(
        "markers", "parity: marks backend parity tests"
    )
```

---

## 六、时间表

| 阶段 | 任务 | 时间 | 交付物 |
|------|------|------|--------|
| **阶段 1** | 基础类型统一 | 第 1 周 | `types.py`, 更新后的 Subprocess 模块 |
| **阶段 2** | 方法签名统一 | 第 2 周 | 更新后的 `database.py`, `pyo3/src/database.rs` |
| **阶段 3** | 后端统一 | 第 3 周 | `backend.py`, 统一的 `Database` 类 |
| **阶段 4** | PyO3 功能完善 | 第 4 周 | 添加 `dump`, `merge`, `create` 功能 |
| **测试** | 完整测试验证 | 第 5 周 | 133+ 测试全部通过 |

---

## 七、风险与缓解

### 7.1 风险识别

| 风险 | 影响 | 可能性 | 严重性 |
|------|------|--------|--------|
| API 变更导致现有代码不兼容 | 高 | 中 | 高 |
| PyO3 功能实现复杂 | 中 | 高 | 中 |
| 测试覆盖不完整 | 高 | 低 | 高 |
| 性能下降 | 高 | 低 | 高 |

### 7.2 缓解措施

1. **向后兼容性**
   - 保持旧方法名作为别名
   - 添加弃用警告而不是直接移除
   - 提供迁移指南

2. **渐进式迁移**
   - 分阶段实施
   - 每个阶段都进行测试验证
   - 保持主分支可工作状态

3. **全面测试**
   - 现有测试必须全部通过
   - 添加后端一致性测试
   - 添加性能基准测试

---

## 八、成功标准

### 8.1 功能标准

- ✅ 133+ 测试全部通过
- ✅ Subprocess 和 PyO3 返回相同结果
- ✅ 统一 API 覆盖所有功能
- ✅ PyO3 具备完整功能（dump, merge, create）

### 8.2 性能标准

- ✅ PyO3 后端性能无下降
- ✅ Subprocess 后端性能无下降
- ✅ 自动后端选择正常工作

### 8.3 文档标准

- ✅ 更新 API 文档
- ✅ 添加迁移指南
- ✅ 更新示例代码

---

**计划制定完成！**
