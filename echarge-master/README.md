# E-Charge 聚合平台（毕业设计骨架）

本项目基于原型设计 [`E-Charge 管理平台`](https://v0-e-charge-platform-design-2a.vercel.app/) 搭建，采用 **前后端分离架构**：

- 前端：Vue 3 + Vite + Element Plus
- 后端：Python + FastAPI
- 数据库：MySQL（通过 SQLAlchemy 连接）

---

## 项目目录结构总览

```text
.
├── app/                     # 后端应用包（导入根）
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── routes.py              # v1 API 路由
│   ├── core/
│   │   └── config.py                  # 环境配置与 MySQL 连接字符串生成
│   ├── db/
│   │   └── database.py                # SQLAlchemy Engine / Session 工厂与 get_db 依赖
│   ├── models/                        # SQLAlchemy 模型
│   ├── schemas/                       # Pydantic Schema
│   └── app.py                         # FastAPI app 实例与路由挂载
│
├── backend/                 # 后端杂项（迁移、脚本、历史文件）
│
├── frontend/               # 前端 Vue 3 + Vite 项目
│   ├── src/
│   │   ├── api/
│   │   │   ├── http.js               # Axios 实例，默认使用 /api/v1（由 Vite 代理到后端）
│   │   │   └── overview.js           # 概览相关 API 封装
│   │   ├── layouts/
│   │   │   └── MainLayout.vue        # 主框架：侧边栏 + 顶栏 + router-view
│   │   ├── router/
│   │   │   └── index.js              # Vue Router 路由配置
│   │   ├── views/
│   │   │   ├── Dashboard.vue         # 概览页（仪表盘）
│   │   │   └── PlaceholderPage.vue   # 其他功能占位页
│   │   ├── App.vue                   # 根组件，使用 MainLayout
│   │   └── main.js                   # Vue 入口，挂载 Element Plus / Router / Pinia
│   └── ...                           # Vite 默认文件（package.json、vite.config.js 等）
│
├── main.py                # Uvicorn 入口：导出 app.app.app
├── requirements.txt       # Python 依赖
└── README.md
```

---

## 后端启动方式（FastAPI）

### 1. 创建并启动虚拟环境（建议）

```bash
cd e:/myproject
python -m venv venv
venv\Scripts\activate  # Windows PowerShell
pip install -r requirements.txt
```

### 2. 设置数据库连接（MySQL）

在项目根目录创建 `.env` 文件（可按实际环境修改）：

```env
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=e_charge

# 或者直接给完整连接字符串（会覆盖上面配置）
# SQLALCHEMY_DATABASE_URI=mysql+pymysql://user:password@host:3306/dbname
```

`app/core/config.py` 会根据这些变量生成 `mysql+pymysql://...` 连接字符串，供 SQLAlchemy 使用。

### 3. 启动后端服务

```bash
uvicorn main:app --reload --port 8000
```

启动完成后，主要测试端点：

- 健康检查：`GET http://localhost:8000/api/v1/health`
- 概览卡片数据：`GET http://localhost:8000/api/v1/overview/summary`
- 实时充电订单：`GET http://localhost:8000/api/v1/overview/realtime-orders`

---

## 前端启动方式（Vue 3 + Element Plus）

```bash
cd e:/myproject/frontend
npm install        # 已在本次初始化执行过，首次建议再确认一次
npm run dev
```

默认会在 `http://localhost:5173` 启动开发服务器。

前端通过 `src/api/http.js` 访问后端：

- `VITE_API_BASE_URL`（若在 `frontend/.env` 设置），例如：

  ```env
  VITE_API_BASE_URL=http://localhost:8000/api/v1
  ```

- 若未设置，默认使用相对路径 `/api/v1`，并由 `vite.config.js` 代理到 `http://localhost:8000/api/v1`（可避免浏览器 CORS）。

---

## 对应原型的基础框架说明

根據原型 [`E-Charge 管理平台`](https://v0-e-charge-platform-design-2a.vercel.app/)：

- **左侧导航菜单**：在 `MainLayout.vue` 中使用 Element Plus `el-menu` 实现，包括：
  - 概览
  - 订单管理（历史订单 / 实时订单 / 异常订单）
  - 财务管理（绑卡管理 / 收益对账 / 开票管理）
  - 电站电桩管理（电站列表 / 电桩管理 / 电价设置 / 审核管理）
  - 机构管理（运营商资料 / 专属机构）
  - 用户管理（专属用户 / 车队管理 / 白名单管理）
  - 营销管理（标签管理 / 折扣管理）
  - 系统设置

- **顶部栏位**：展示当前页面标题与用户信息：
  - 角色：运营商管理员
  - 账号：`admin@echarge.com`

- **概览页（Dashboard）**：
  - 四张统计卡片：今日订单、今日收益、在线电桩、活跃用户
  - 两块图表区域（目前保留为“预留图表区”，后续可接入 ECharts / AntV 等）
  - “实时充电订单”表格，数据来自后端假数据 API

后续你可以在 `views/` 目录下为每个二级菜单建立独立页面，并对应到后端 `app/api/v1/` 中的具体业务路由与数据模型。

---


## 角色边界重构（管理员 vs 运营商）

前端新增了统一的权限配置文件 `frontend/src/config/permissions.js`，将“菜单显示 + 路由可访问性 + 默认首页”集中管理，避免一个页面同时承载两种角色逻辑导致混乱。

- 管理员：平台治理（审核、清分、合规、全局配置）
- 运营商：经营动作（订单处理、站桩运营、营销、对账）

同时新增 `职责蓝图` 页面（`/role-blueprint`）用于沉淀职责矩阵与流程建议，你可以把它当做毕业设计答辩时的“业务架构页”。

## 下一步建议

- 在 `app/models/` 定义核心实体（电站、电桩、订单、用户、运营商等）并建立 Alembic 迁移。
- 在 `app/api/v1/` 按业务模块拆分路由文件（如 `orders.py`、`stations.py` 等）。
- 在前端 `views/` 下，逐步将 `PlaceholderPage.vue` 替换为真实的功能页面。


---

## 核心业务联调说明

### 1. 初始化数据库与演示数据

```bash
python scripts/init_demo_data.py
```

脚本特性：
- 可重复执行，会优先更新固定演示账号、运营商、站点、电桩、订单、钱包流水、发票与清分记录。
- 如果数据库表还没创建，脚本会自动调用 `Base.metadata.create_all(bind=engine)`。
- 执行完成后会打印 `operator_id`、`station_id`、`charger_sn`、`user_id` 与可直接测试的订单号。

### 2. 启动后端

```bash
uvicorn main:app --reload --port 8000
```

### 3. 启动前端

```bash
cd frontend
npm run dev
```

### 4. Swagger 演示接口

启动后可在 Swagger 中看到新增的演示接口：
- `/api/v1/demo/flow/health`
- `/api/v1/demo/orders/*`
- `/api/v1/demo/stations/*`
- `/api/v1/demo/settlements/*`
- `/api/v1/demo/invoices/*`

### 5. 推荐演示链路

1. 运营商进入“电站管理”，提交一个新电站申请。
2. 管理员进入“电站审核”，对刚提交的电站执行“审核通过”或“驳回”。
3. 运营商回到“电站管理 / 电桩管理 / 电价设置”，为已审核电站添加电桩并绑定计费模板。
4. 运营商进入“实时订单”，点击“演示创建订单”。
5. 在“实时订单”中结束订单，观察订单流转到“历史订单”，并生成钱包扣费流水。
6. 管理员进入“平台清分中心”，选择已完成未清分订单所属日期，执行 T+1 清分。
7. 运营商进入“收益对账”，查看清分结果、平台服务费与待打款 / 挂起状态。
8. 进入“发票管理”，先提交演示发票申请，再处理为“已开票”或“已驳回”。

### 6. 当前毕业设计中的模拟实现说明

以下能力当前仍为毕业设计演示级模拟实现：
- 订单开始 / 结束不接真实充电桩，仅通过演示接口修改电桩与订单状态。
- 钱包扣费与充值不接真实支付渠道，仅写入 `WalletTransaction` 演示流水。
- T+1 清分不做真实银行打款，仅生成运营商清分记录与挂起原因。
- 发票处理不接真实税控或邮件平台，邮件通知默认走日志模拟。
- 管理员 / 运营商身份通过前端角色上下文与演示数据切换，不接真实登录鉴权。

---

## 核心业务联调说明（答辩 MVP 修正版）

### 推荐执行顺序

```bash
python scripts/patch_demo_schema.py
python scripts/init_demo_data.py
uvicorn main:app --reload --host 127.0.0.1 --port 8000
cd frontend
npm run dev
```

`patch_demo_schema.py` 会在不清空业务数据、不删除表的前提下检查并补齐演示主链所需字段，兼容 MySQL 5.6。后续直接执行 `python scripts/init_demo_data.py` 也会自动先执行同等结构检查。

### 演示链路

1. 运营商进入“电站管理”，提交一个新电站申请。
2. 管理员进入“电站审核”，审核通过后电站写入数据库为 `status=0`、`visibility=public`。
3. 运营商刷新电站列表，给已审核电站新增电桩并绑定电价模板。
4. 进入“实时订单”，点击“演示创建订单”，选择空闲电桩创建订单。
5. 点击“结束订单”，订单进入历史订单，电桩恢复空闲，钱包消费流水写入数据库。
6. 点击“标记异常”，订单进入异常订单，电桩变为故障。
7. 管理员在“清分中心”选择订单结束日期执行清分，生成运营商清分记录并更新订单 `settle_status=1`。
8. 运营商在“收益对账”查看同一条清分记录。
9. 在“发票管理”申请发票，确认开具后状态写入数据库为已开票并刷新列表。

### Schema 补丁覆盖范围

- `trade_orders`: `pay_status`、`settle_status`、`charge_duration`
- `trade_wallet_transactions`: `id`、`user_id`、`transaction_type`、`amount`、`balance_after`、`remark`、`related_order_id`、`created_at`
- `trade_invoices`: `user_id`、`operator_id`、`order_id`、`invoice_title`、`amount`、`email`、`status`、`file_url`、`uploaded_at`、`remark`
- `trade_operator_settlements`: `settle_date`、`operator_id`、`order_count`、`total_amount`、`platform_rate`、`platform_fee`、`settle_amount`、`status`、`hold_reason`

### 字段验证

```sql
SHOW COLUMNS FROM trade_orders LIKE 'pay_status';
SHOW COLUMNS FROM trade_orders LIKE 'settle_status';
SHOW COLUMNS FROM trade_orders LIKE 'charge_duration';
```

如果清分提示数据库连接失败，请确认 MySQL 已启动，并检查 `.env` 中 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DB` 配置。
