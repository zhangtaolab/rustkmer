# 数据模型：RustKmer CLI 测试

## 核心实体

### 1. 测试数据集 (TestDataset)

```yaml
entity: TestDataset
fields:
  - name: 文件路径 (string, required)
  - name: 文件类型 (enum: FASTA | FASTQ, required)
  - name: 文件大小 (integer, bytes)
  - name: 序列数量 (integer)
  - name: 总碱基数 (integer)
  - name: 预计 k-mer 数量 (integer, for k=31)
```

### 2. 测试场景 (TestScenario)

```yaml
entity: TestScenario
fields:
  - name: 场景ID (string, required)
  - name: 命令 (enum: count | dump | query | fuzzy-query | stats | merge | help)
  - name: 测试参数 (object)
    properties:
      kmer_size: [21, 31, 63]
      parallel_threads: [1, 2, 4, 8]
      input_format: [fasta, fastq]
      output_format: [text, json]
  - name: 预期结果 (object)
    properties:
      exit_code: integer
      output_contains: [string]
      database_created: boolean
```

### 3. 性能指标 (PerformanceMetrics)

```yaml
entity: PerformanceMetrics
fields:
  - name: 执行时间 (float, seconds)
  - name: 用户CPU时间 (float, seconds)
  - name: 系统CPU时间 (float, seconds)
  - name: 最大RSS内存 (integer, KB)
  - name: 平均RSS内存 (integer, KB)
  - name: 上下文切换次数 (integer)
  - name: 页面错误次数 (integer)
  - name: 磁盘读取量 (integer, bytes)
  - name: 磁盘写入量 (integer, bytes)
```

### 4. 测试结果 (TestResult)

```yaml
entity: TestResult
fields:
  - name: 测试ID (string, required)
  - name: 场景ID (string, foreign key: TestScenario)
  - name: 数据集路径 (string, foreign key: TestDataset)
  - name: 执行状态 (enum: PASSED | FAILED | ERROR)
  - name: 性能指标 (PerformanceMetrics)
  - name: 输出文件列表 ([string])
  - name: 错误消息 (string, optional)
  - name: 验证结果 (object)
    properties:
      功能正确性: boolean
      输出格式正确: boolean
      数据完整性: boolean
```

### 5. 测试报告 (TestReport)

```yaml
entity: TestReport
fields:
  - name: 报告ID (string, required)
  - name: 生成时间 (datetime, required)
  - name: rustkmer版本 (string)
  - name: 系统环境 (object)
    properties:
      操作系统: string
      CPU信息: string
      内存总量: string
      Rust版本: string
  - name: 测试结果汇总 (object)
    properties:
      总测试数: integer
      通过数: integer
      失败数: integer
      错误数: integer
      成功率: float (percentage)
  - name: 性能摘要 (object)
    properties:
      平均执行时间: float
      最大内存使用: integer
      并行效率: [float] # 每个线程数的效率
  - name: 发现的问题 ([Issue])
```

### 6. 问题记录 (Issue)

```yaml
entity: Issue
fields:
  - name: 问题ID (string, required)
  - name: 严重程度 (enum: CRITICAL | HIGH | MEDIUM | LOW)
  - name: 类型 (enum: BUG | PERFORMANCE | DOCUMENTATION | FEATURE)
  - name: 描述 (string, required)
  - name: 重现步骤 ([string])
  - name: 期望行为 (string)
  - name: 实际行为 (string)
  - name: 建议修复 (string, optional)
```

## 实体关系图

```
TestDataset (1) -----> (N) TestScenario
    |                          |
    |                          v
    +------------> (N) TestResult -----> (1) TestReport
                              |
                              v
                        PerformanceMetrics

TestResult (1) -----> (N) Issue
```

## 数据验证规则

### 测试数据集验证
- 文件必须存在且可读
- 文件格式必须是有效的 FASTA 或 FASTQ
- 文件大小必须 > 0

### 测试结果验证
- exit_code = 0 表示成功执行
- 对于 count 命令，必须生成 .rkdb 文件
- 对于 query 命令，输出格式必须符合预期
- 内存使用不能超过系统限制

### 性能基准验证
- 执行时间 < 预期阈值（如 1GB 数据 < 10 分钟）
- 内存使用 < 8GB
- 并行效率应随线程数增加而提升（到达某个点后可能下降）

## 状态转换

### 测试执行状态流
```
PENDING -> RUNNING -> (PASSED | FAILED | ERROR)
   ^         |
   |---------+
```

## 数据持久化

### 文件存储结构
```
/Users/forrest/Temp/demodata/rustkmer_cli_test/
├── test_results.json          # 所有测试结果
├── performance_metrics.json   # 性能数据
├── test_report_YYYYMMDD.md    # 生成的测试报告
└── issues.json               # 发现的问题列表
```

### JSON Schema 示例

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "test_results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "test_id": {"type": "string"},
          "scenario_id": {"type": "string"},
          "dataset_path": {"type": "string"},
          "status": {"enum": ["PASSED", "FAILED", "ERROR"]},
          "metrics": {
            "type": "object",
            "properties": {
              "execution_time": {"type": "number"},
              "max_rss": {"type": "integer"}
            }
          }
        }
      }
    }
  }
}
```