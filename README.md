# TickHub · 在线票务预订系统

前后端分离的在线票务后端，提供场次浏览、座位图、座位锁定与下单能力，
重点解决**高并发抢座场景下的超卖问题**。

## 功能

- **用户认证**：注册、登录（bcrypt 密码哈希）、Token 鉴权、获取当前用户
- **场次**：创建场次、场次列表（按开演时间排序）
- **座位**：按「排 × 列」批量生成座位、座位图查询（含实时锁定状态）
- **锁座**：座位锁定 15 分钟，支持续期与过期接管
- **下单**：锁 → 订单 → 座位售出（单事务），一个座位只能成交一次
- **我的订单**：按用户隔离，支持分页

## 技术栈

| 分类 | 选型 |
|---|---|
| Web 框架 | FastAPI 0.151 |
| ORM | SQLAlchemy 2.0（async）+ aiomysql |
| 数据库 | MySQL 8.0 |
| 缓存 / 分布式锁 | Redis 7 |
| 数据校验 | Pydantic v2 + pydantic-settings |
| 密码安全 | bcrypt |
| 部署 | Docker + Docker Compose |
| 测试 | pytest + pytest-asyncio + httpx |

## 系统架构

```text
┌──────────────┐     HTTP/JSON     ┌─────────────────────────────────┐
│   客户端      │ ────────────────→ │  FastAPI (uvicorn)              │
│ (前端/接口文档)│ ←──────────────── │  api → services → repositories  │
└──────────────┘                   └───────┬─────────────────┬───────┘
                                           │                 │
                                   ┌───────▼──────┐   ┌──────▼───────┐
                                   │   Redis 7    │   │   MySQL 8    │
                                   │ 缓存/分布式锁 │   │  持久化存储   │
                                   └──────────────┘   └──────────────┘
```

分层职责：

| 层 | 目录 | 职责 |
|---|---|---|
| 路由层 | `app/api/v1/` | 接请求、参数校验、返回响应，不写业务与 SQL |
| 业务层 | `app/services/` | 业务规则、事务边界、异常语义 |
| 数据层 | `app/repositories/` | 只负责 SQL，不做业务判断 |
| 模型层 | `app/models/` | 表结构、约束定义 |
| 入参出参 | `app/schemas/` | 请求/响应格式与白名单 |
| 基础设施 | `config.py` `database.py` `dependencies.py` `cache.py` `utils/` | 配置、连接、鉴权、缓存、工具 |

## 快速开始

前置：Docker Desktop。

```bash
docker compose up -d --build
```

三个服务启动后访问接口文档：<http://127.0.0.1:8000/docs>

| 服务 | 地址 |
|---|---|
| API | http://127.0.0.1:8000 |
| MySQL | 127.0.0.1:3307（root / 123456） |
| Redis | 127.0.0.1:6379 |

## 本地开发

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

首次运行需要建表：

```bash
python create_tables.py
```

## 接口一览

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| POST | `/api/v1/auth/register` | 否 | 注册（用户名重复返回 409） |
| POST | `/api/v1/auth/login` | 否 | 登录，返回 Token |
| GET | `/api/v1/auth/me` | 是 | 获取当前用户 |
| GET | `/api/v1/shows` | 否 | 场次列表（带缓存） |
| POST | `/api/v1/shows` | 是 | 创建场次 |
| POST | `/api/v1/shows/{show_id}/seats/generate` | 是 | 批量生成座位 |
| GET | `/api/v1/shows/{show_id}/seats` | 是 | 座位图（含锁定状态） |
| POST | `/api/v1/shows/{show_id}/seats/{seat_id}/lock` | 是 | 锁定座位（15 分钟） |
| POST | `/api/v1/orders` | 是 | 下单 |
| GET | `/api/v1/orders` | 是 | 我的订单（分页） |

## 设计说明

### 1. 防超卖：两层防线

抢座的核心矛盾是：多个请求在同一时刻都判断"这个座位没人锁"，然后都去插入。
应用层的"先查再插"挡不住这种并发，因为两个请求可能同时通过检查。

因此采取两层防护：

- **第一层：Redis 分布式锁**（`SET key value NX EX`），锁粒度为单个座位。
  请求先抢 `seat:lock:{seat_id}`，抢不到直接返回 409，把绝大多数并发挡在数据库之外，
  避免无谓的事务回滚；value 使用随机 token，释放时用 Lua 脚本校验 token 后再删除，防止误删他人的锁。
- **第二层：数据库唯一约束**。`seat_locks.seat_id` 与 `orders.seat_id` 都建立了唯一索引。
  即使锁失效、请求绕过第一层，数据库也只允许写入一行，冲突时抛出 `IntegrityError`，
  由业务层转换为 409，不会出现同一座位被两人成交。

**两层都保留的原因**：Redis 在主从切换期间可能丢失锁，锁本身不是绝对可靠的；
而数据库唯一约束由存储引擎保证，不会因网络分区失效。
一句话概括：**锁负责降低冲突，约束负责保证正确。**

### 2. 缓存策略

采用 Cache-Aside 模式：

- **TTL 按数据变化频率区分**：场次列表读多写少，TTL 60 秒；座位图状态是秒级变化的
  （锁定、售出、锁过期），TTL 只给 5 秒。
- **缓存只存公共数据**：座位号、价格、锁持有人 id、锁过期时间进入缓存；
  而 `is_locked` 与 `locked_by_me` 在响应时按当前用户和当前时间**实时计算**。
  这样同一份缓存可以服务所有用户——既不会把别人的锁显示成"我的"，
  锁过期后即使缓存未刷新也会立即反映为可售。
- **写操作后删除缓存而非更新缓存**：创建场次、生成座位、锁座、下单成功后都删除对应 key，
  下次读取时自然回填，避免并发写入造成覆盖。
- **缓存降级**：所有缓存调用都捕获异常，Redis 不可用时直接回源数据库，
  接口保持可用（实测停掉 Redis 后接口仍返回 200）。

### 3. 开发中踩的坑

- **模型没被导入时，`create_all` 不会建表，而且不报错。** 因为 SQLAlchemy 只认识"已登记的模型"，
  后来在 `models/__init__.py` 中集中导入全部模型，才彻底避免这种依赖导入顺序的隐性问题。
- **`create_all` 不会修改已存在的表。** 给 `users` 加 `token` 字段后，重新执行建表脚本毫无反应，
  最终改用"删表重建"解决，并明确后续应由 Alembic 迁移承担。
- **座位缓存未失效会造成"已锁座位显示可点"。** 用户点进去才收到 409，体验很差，
  因此在锁座与下单成功后主动删除座位缓存 key，并在响应时用过期时间实时判断锁定状态。

## 测试

```bash
pytest -v
```

覆盖范围（8 个用例）：

- 认证：注册不泄露密码哈希、重名 409、弱密码 422、密码错误 401、无/假 Token 401
- 业务：**两人并发抢同一座位只有一人成功**、下单必须持有有效锁、一个座位只能成交一次、订单按用户隔离

测试隔离方式：独立数据库 `tickhub_test` + Redis 1 号库 + `ASGITransport` 直连应用。

## 项目结构

```text
tickhub/
├── app/
│   ├── main.py                 # 应用入口、路由注册、过期锁清理任务
│   ├── config.py               # 配置（pydantic-settings）
│   ├── database.py             # 异步引擎、会话工厂、Base
│   ├── dependencies.py         # get_current_user 鉴权依赖
│   ├── cache.py                # Redis 客户端与 JSON 缓存封装
│   ├── api/v1/                 # auth / show / order 路由
│   ├── models/                 # 5 张表模型
│   ├── schemas/                # 请求/响应模型
│   ├── repositories/           # 数据访问层
│   ├── services/               # 业务逻辑层
│   └── utils/                  # 密码哈希、Redis 分布式锁
├── tests/                      # conftest + 认证/业务测试
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── create_tables.py            # 建表脚本
```

## 后续计划

- [ ] 角色权限（admin / user），创建场次与生成座位仅管理员可用
- [ ] Alembic 数据库迁移，替代开发期的重建表
- [ ] 接口限流（Redis 计数器），防止恶意刷单
- [ ] CI（GitHub Actions）：push 自动跑 pytest

## 关于

个人求职作品 · 挽枫临 · 20230024032@qq.com

如果这个项目对你有帮助，欢迎点个 Star。
