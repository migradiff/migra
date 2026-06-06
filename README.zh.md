# MigraDiff

<div align="center">

**选择语言:**  
[English](README.md) | 
[हिन्दी](README.hi.md) | 
[中文](README.zh.md) | 
[日本語](README.ja.md) | 
[Français](README.fr.md) | 
[Deutsch](README.de.md) | 
[עברית](README.he.md)

</div>

---

# migra — PostgreSQL 模式差异对比工具

[![PyPI version](https://img.shields.io/pypi/v/migradiff)](https://pypi.org/project/migradiff/)
[![Python versions](https://img.shields.io/pypi/pyversions/migradiff)](https://pypi.org/project/migradiff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**这是 [djrobstep/migra](https://github.com/djrobstep/migra) 的活跃维护分支。**

migra 比较两个 PostgreSQL 数据库模式，并生成将一个模式转换为另一个模式所需的 SQL 迁移脚本。将其放入 CI 流水线中，告别手动编写 `ALTER TABLE`。

---

## 为什么使用这个分支

原始 `migra` 已于 2024 年正式弃用。这个分支在此基础上继续发展——修复已知问题、添加 Python 3.12+ 支持，并扩展对高级 PostgreSQL 功能的覆盖。

如果您以前使用 `djrobstep/migra`，这是您的直接替代方案。工具的工作方式没有任何改变。我们只是保持它的持续运行并变得更好。

**关于命名的说明：** 这是一个独立的社区分支。CLI 命令保持为 `migra`，以保持与现有脚本和流水线的向后兼容性。包名改为 `migradiff` 以区别于已弃用的上游版本。如果您在寻找原始的 djrobstep/migra，它已归档在 https://github.com/djrobstep/migra。

---

## 快速开始

### 安装

```bash
pip install migradiff
```

需要 Python 3.10+ 和运行中的 PostgreSQL 实例（12+）。

从源码安装：

```bash
git clone https://github.com/migradiff/migra
cd migra
pip install -e .
```

### 基本用法

将 migra 指向两个数据库连接，它会输出从一个迁移到另一个所需的 DDL：

```bash
migra \
  postgresql://user:pass@localhost/db_production \
  postgresql://user:pass@localhost/db_branch \
  --unsafe
```

输出是纯 SQL —— 可以管道传输、审查、应用：

```bash
migra postgres://db_a postgres://db_b > migration.sql
psql postgres://db_production < migration.sql
```

### 模式转储（无需实时连接）

如果您不能或不想将 migra 指向实时数据库，可以使用 `pg_dump -s` 生成模式转储并进行差异对比：

```bash
pg_dump -s postgres://db_production > schema_a.sql
pg_dump -s postgres://db_branch     > schema_b.sql
migra --from-file schema_a.sql schema_b.sql
```

这是 CI 流水线和对安全敏感的环境的推荐方法 —— 无需生产凭据。

### 迁移目录（无需实时分支数据库）

如果您的目标状态由迁移文件文件夹定义：

```bash
migra --from-migrations-dir ./migrations postgres://db_production
```

MigraDiff 将迁移应用到临时数据库并对结果进行差异对比。支持 Supabase、Flyway 和标准数字命名规范。

### 限定到某个模式

```bash
# 单个模式
migra --schema myschema postgres://db_a postgres://db_b

# 多个模式（逗号分隔）
migra --schema public,reporting postgres://db_a postgres://db_b
```

### JSON 输出

适用于程序化使用或 CI 流水线：

```bash
migra --output json postgres://db_a postgres://db_b
```

输出包含每条语句的风险分类（`safe`、`warning`、`destructive`）和包含总体风险级别的摘要。

---

## AI 驱动的解释（可选）

MigraDiff 可以用通俗易懂的语言解释任何迁移 —— 每个变更的作用、带来的风险，以及破坏性操作的更安全替代方案。

    migra --explain postgres://db_a postgres://db_b

输出：

    --- Migration SQL ---
    ALTER TABLE public.users ADD COLUMN email text;
    DROP TABLE public.legacy_sessions;

    --- AI Explanation ---
    This migration makes 2 changes to your database:

    1. SAFE: Adds an email column (text) to the users table.
       No existing data is affected.

    2. ⚠ DESTRUCTIVE: Drops the legacy_sessions table entirely.
       All data in this table will be permanently lost.
       Consider archiving before dropping.

    Overall risk: HIGH

由 Claude（Anthropic）提供支持。请自带 API 密钥 —— 不会有数据发送到 MigraDiff 服务器。

### 设置

安装 AI 额外组件：

    pip install migradiff[ai]

一次性配置您的 API 密钥：

    migra --setup-ai

或设置环境变量：

    export ANTHROPIC_API_KEY=sk-ant-...

在 https://console.anthropic.com 获取 API 密钥。

### AI 回滚生成（--rollback）

生成精确的反向迁移 —— 撤销任何迁移所需的 SQL：

    migra --rollback migration.sql
    migra --rollback postgres://db_a postgres://db_b

MigraDiff 使用您的源模式上下文来准确重建 DROP TABLE 和 DROP COLUMN 的逆转操作。不可逆操作（TRUNCATE、批量 DELETE）会被明确标记。

与 --explain 结合使用以获得完整视图：

    migra --explain --rollback postgres://db_a postgres://db_b

需要 `pip install migradiff[ai]` 和 Anthropic API 密钥。

### AI 性能顾问（--advise）

在应用任何迁移之前，获取性能风险评估 —— 锁定行为、表重写风险和零停机替代方案：

    migra --advise postgres://db_a postgres://db_b
    migra --advise migration.sql

MigraDiff 分析每条语句是否存在 PostgreSQL 特定风险：表锁、完全重写、不可逆的数据丢失。当提供实时连接时，表行计数用于估算实际数据规模下的锁定持续时间。

结合所有三种 AI 功能以获得完整视图：

    migra --explain --advise --rollback postgres://db_a postgres://db_b

需要 pip install migradiff[ai] 和 Anthropic API 密钥。

### AI 迁移生成器（--generate）

用通俗易懂的语言描述您的需求 —— MigraDiff 基于您的实际模式生成迁移 SQL：

    migra --generate "add email verification to users table" \
      postgres://db_production

与通用 AI 工具不同，MigraDiff 知道您的真实表名、列类型和约束 —— 不会出现虚构的列名或错误的类型。

生成并立即审查风险：

    migra --generate "add index on orders.user_id" \
      --advise postgres://db_production

需要 pip install migradiff[ai] 和 Anthropic API 密钥。

---

## 开发环境搭建

测试套件需要一个运行中的 PostgreSQL 实例。最简单的方式是通过 Docker Compose：

```bash
docker compose up -d
```

这会在 localhost:5432 上启动一个使用信任认证的 Postgres 16 容器。无需密码。

停止：

```bash
docker compose down
```

数据通过 `migradiff-pgdata` 卷在重启之间持久化。完全重置：

```bash
docker compose down -v
```

---

## Docker

没有 Python 环境？使用官方镜像：

```bash
docker run --rm ghcr.io/migradiff/migra \
  postgres://db_a postgres://db_b
```

---

## GitHub Actions

将模式差异对比添加到您的拉取请求工作流中：

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
```

检测到破坏性操作时自动使构建失败：

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
    fail_on_destructive: "true"
```

使用模式转储文件而不是实时连接：

```yaml
- uses: migradiff/migra@v1
  with:
    base_file: schema_production.sql
    head_file: schema_branch.sql
```

完整配置选项请参阅 [docs/action-usage.md](docs/action-usage.md)。

---

## Pre-commit 钩子

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/migradiff/migra
    rev: v1.1.0
    hooks:
      - id: migra
```

完整配置选项请参阅仓库根目录中的 `pre-commit-config.example.yaml`。

---

## migra 理解的内容

- 表、列、约束、索引
- 视图和物化视图
- 函数和存储过程
- 序列
- 枚举、复合类型、域
- 行级安全（RLS）策略
- 外部数据包装器
- 列级权限
- 分区表
- 对象注释（`COMMENT ON`）

---

## 相较于上游的改进

| 领域 | 上游（已弃用） | 本分支 |
|---|---|---|
| Python 3.12+ | 弃用警告 | 干净 —— 无警告 |
| RLS 策略 | 部分，存在相等性错误 | 完整的 CREATE/DROP，分区支持 |
| 错误消息 | 不支持的类型时含义模糊 | 可操作，包含对象名称和问题链接 |
| --schema 标志 | 多模式数据库中存在边缘情况 | 逗号分隔，跨模式依赖已解决 |
| pg_dump 输入 | 不支持 | 一流的 `--from-file` 模式 |
| JSON 输出 | 不支持 | `--output json` 带风险分类 |
| Docker 镜像 | 无 | `ghcr.io/migradiff/migra` |
| GitHub Action | 无 | `migradiff/migra-action` |
| Pre-commit 钩子 | 无 | `.pre-commit-hooks.yaml` |
| 开发环境 | 手动 Docker 命令 | `docker compose up -d` |
| AI 解释 | 无 | `--explain` 标志配合 Claude —— 通俗语言差异解释、风险分析、更安全的替代方案 |
| COMMENT ON 差异对比 | 不支持 | 所有对象类型的完整差异对比 —— 添加/更改/删除 |

完整修复历史请参阅 [CHANGELOG.md](CHANGELOG.md)。

---

## 已知限制

migra 生成 SQL 差异 —— 它不应用差异。在针对生产环境运行之前，请审查每个生成的脚本。破坏性操作（`DROP TABLE`、`DROP COLUMN`）在 JSON 输出模式下会被标记，但在纯 SQL 模式下不会被阻止。

migra 需要实时 PostgreSQL 连接来内省模式，或通过 `--from-file` 提供模式转储文件。它不解析原始 DDL 文本。

---

## 贡献须知

感谢您对这个项目的关注。请注意，我们目前不接受任何外部代码贡献、拉取请求、错误修复或功能提交。

任何打开的拉取请求将自动关闭，恕不审查。

---

## 许可

MigraDiff 在 MIT 许可证下是**免费且开源的**。

**所有功能对所有人都可用。** 没有付费墙，没有代码限制，没有封闭管理。

### 一个小故事

我曾在飞利浦担任工程师 8 年以上，支持保障患者安全的医院 IT 系统。当收购我们部门的 VC 解雇我时，我已经 50 多岁了，在一个年龄很重要的市场中。找到另一份工作几乎变得不可能。我仍然需要养家糊口。

这就是 MigraDiff 存在的原因。我正在构建帮助您的工具，因为这是我保持就业的方式。

### 请求

**如果您是学生、爱好者或开源项目：** MIT 许可证，永远免费。无需任何协议。

**如果您是使用 MigraDiff 的营利性公司：** 请签署商业许可协议。这不是关于封闭代码——每个功能都保持免费，您在本地运行它，技术上对您没有任何改变。这是关于公平：如果我的工具正在帮助您赚钱，请帮助我养家糊口。

您仍然拥有一切。您控制您的数据。您可以访问所有功能。我们只是在如何维持开发方面保持透明。

我不是在乞求施舍。我是在要求公平。

[获取商业许可](https://lateos.ai/license) | [查看 MIT 许可证](LICENSE)

---

## 致谢

本项目是 [djrobstep/migra](https://github.com/djrobstep/migra) 的一个分支，由 Robert Lechte 创建并最初维护。核心差异对比引擎是他的工作。我们对此深表感谢。
