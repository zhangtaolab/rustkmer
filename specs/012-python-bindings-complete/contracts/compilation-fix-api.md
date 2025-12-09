# 编译修复API规范

**日期**: 2025-12-09
**版本**: 1.0

## 概述

本文档定义了修复RustKmer编译问题的API接口和操作流程。

## 端点列表

### 1. 修复未使用变量

#### POST /api/v1/fixes/unused-variables

修复代码中未使用的变量。

**请求体**:
```json
{
  "variables": [
    {
      "file_path": "src/database/format.rs",
      "line_number": 590,
      "variable_name": "kmer_size",
      "action": "prefix"
    }
  ]
}
```

**响应**:
```json
{
  "status": "success",
  "fixed_count": 3,
  "details": [
    {
      "file": "src/database/format.rs",
      "line": 590,
      "message": "Prefixed variable with underscore"
    }
  ]
}
```

### 2. 修复未使用字段

#### POST /api/v1/fixes/unused-fields

修复结构体中未使用的字段。

**请求体**:
```json
{
  "fields": [
    {
      "struct_name": "FuzzyQuery",
      "field_name": "max_distance",
      "action": "implement_usage"
    }
  ]
}
```

**响应**:
```json
{
  "status": "success",
  "fixed_count": 2,
  "details": [
    {
      "struct": "FuzzyQuery",
      "field": "max_distance",
      "message": "Implemented field usage in search method"
    }
  ]
}
```

### 3. 配置链接设置

#### POST /api/v1/config/linking

配置平台特定的链接设置。

**请求体**:
```json
{
  "platform": "aarch64-apple-darwin",
  "python_lib_path": "/Users/forrest/miniconda3/lib",
  "python_version": "3.13"
}
```

**响应**:
```json
{
  "status": "success",
  "config_file": ".cargo/config.toml",
  "rustflags": [
    "-C", "link-arg=-L/Users/forrest/miniconda3/lib",
    "-C", "link-arg=-lpython3.13",
    "-C", "link-arg=-Wl,-rpath,/Users/forrest/miniconda3/lib"
  ]
}
```

### 4. 验证编译状态

#### GET /api/v1/validation/compilation

检查当前编译状态。

**查询参数**:
- `mode`: 编译模式 (debug|release)
- `features`: 特性标志 (如 python)

**响应**:
```json
{
  "status": "success",
  "mode": "release",
  "warnings": 0,
  "errors": 0,
  "build_successful": true,
  "details": {
    "command": "cargo build --release --features python",
    "duration": "45.2s",
    "artifacts": [
      "target/release/librustkmer.dylib",
      "target/release/rustkmer"
    ]
  }
}
```

### 5. 获取修复进度

#### GET /api/v1/fixes/progress

获取修复任务的整体进度。

**响应**:
```json
{
  "total_issues": 5,
  "fixed_issues": 5,
  "pending_issues": 0,
  "completion_percentage": 100,
  "breakdown": {
    "unused_variables": 3,
    "unused_fields": 2,
    "linking_issues": 0
  }
}
```

## 数据类型

### FixAction

```rust
enum FixAction {
    Prefix,        // 添加下划线前缀
    Remove,        // 删除
    Implement,     // 实现使用
    Allow,         // 允许死代码
}
```

### CompilationStatus

```rust
struct CompilationStatus {
    success: bool,
    warnings: Vec<Warning>,
    errors: Vec<Error>,
    artifacts: Vec<String>,
}
```

### Warning

```rust
struct Warning {
    file_path: String,
    line: u32,
    message: String,
    level: WarningLevel,
}

enum WarningLevel {
    Info,
    Warning,
    Error,
}
```

## 错误处理

### 错误代码

| 代码 | 描述 |
|------|------|
| CF001 | 找不到文件 |
| CF002 | 无法解析变量 |
| CF003 | 写入文件失败 |
| CF004 | 配置无效 |
| CF005 | 编译失败 |

### 错误响应格式

```json
{
  "error": {
    "code": "CF001",
    "message": "File not found",
    "details": "src/database/format.rs does not exist",
    "timestamp": "2025-12-09T10:30:00Z"
  }
}
```

## 认证

所有API端点都需要API密钥认证。

**请求头**:
```
Authorization: Bearer <API_KEY>
```

## 限制

- 每分钟最多100个请求
- 每次批量修复最多50个项目
- 配置文件大小限制为1MB

## 示例

### 完整修复流程

1. **检查编译状态**
```bash
curl -H "Authorization: Bearer $API_KEY" \
     "https://api.rustkmer.com/api/v1/validation/compilation?mode=release&features=python"
```

2. **修复未使用变量**
```bash
curl -X POST -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d @variables.json \
     "https://api.rustkmer.com/api/v1/fixes/unused-variables"
```

3. **配置链接**
```bash
curl -X POST -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d @linking.json \
     "https://api.rustkmer.com/api/v1/config/linking"
```

4. **验证修复结果**
```bash
curl -H "Authorization: Bearer $API_KEY" \
     "https://api.rustkmer.com/api/v1/validation/compilation?mode=release&features=python"
```

## 版本历史

- **1.0** (2025-12-09): 初始版本，支持基本的编译修复功能