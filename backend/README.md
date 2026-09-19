# FinTaxFlow 后端

FastAPI + PostgreSQL。接口契约见 [`../frontend/API_CONTRACT.md`](../frontend/API_CONTRACT.md)。

整仓（数据库 + API + H5）从仓库根目录 `./start.sh` 或双击 `启动项目.command` 启动。下面是仅启动后端的步骤。

## 本机条件

- Python 3.12（本机实测路径 `/opt/homebrew/bin/python3.12`）
- Docker Desktop，用于本地 PostgreSQL 16
- 不使用 SQLite 替代

## 目录

```text
backend/
├── app/
│   ├── main.py            # 应用入口
│   ├── api/               # HTTP：deps、聚合路由、按域拆分的 routes
│   ├── core/              # 配置、安全、错误、时钟、金额
│   ├── models/            # SQLAlchemy 模型
│   ├── schemas/           # Pydantic 入参/出参
│   ├── services/          # 开票、查询、恢复、PDF、种子
│   └── workers/           # 本地开票处理器
├── migrations/
└── samples/
```

## 首次启动

在仓库根目录：

```sh
docker compose up -d
cd backend
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

日常启动只运行 PostgreSQL 与 `uvicorn`，**不会**自动恢复演示数据。需要重建某企业时走产品内“恢复当前企业”，或删除库后重新 `alembic upgrade head && python -m app.seed`。

API 基址：`http://127.0.0.1:8000/api`。健康检查：`GET /api/health`。

## 演示账号

密码均为 `123456`，登录必须走后端校验。

| 账号 | 姓名 | 企业 |
| --- | --- | --- |
| `demo_boss01` | 李总 | 深圳星河科技有限公司、广州远航企业管理与科技服务有限责任公司 |
| `demo_boss02` | 王总 | 杭州云程科技有限公司、成都青梧数字科技有限公司 |

每个账号的两家企业数据独立。时间口径为 Asia/Shanghai；报税/账务三个月以启动种子或恢复时的当月为基准。

## 配置

复制 `.env.example` 为 `.env`。不要把真实密钥提交进仓库。PDF 文件写入仓库根目录 `var/invoice-pdfs/`，按企业分子目录存放，接口鉴权后读取。

## 导入、对账与模拟申报

新增接口与 HTTP 行为见 [扩展接口契约](../frontend/API_CONTRACT.md#e1-contract)。固定 CSV 样例见 [samples](samples/README.md)。

- 安装更新：激活 `.venv` 后执行 `pip install -e .`；新增运行依赖是 `python-multipart` 和 Python `playwright`。机器人使用本机已安装的 Google Chrome（`RPA_BROWSER_CHANNEL=chrome`），不需要 Node 机器人或 Redis/Celery。
- 增量升级：`alembic upgrade head`，现行版本 `0002`。首版迁移已冻结，增量迁移保留原业务数据。日常启动脚本会执行迁移，不重置演示库。
- 同源 X01：`http://127.0.0.1:8000/simulation-portal/index.html`；普通访问不含凭证，机器人领取任务后签发十分钟的专用凭证。静态文件直接挂载自 `frontend/portal/`。
- 如改变 API 端口，同时设置 `SIMULATION_BASE_URL`。浏览器执行在本地处理器线程内，数据库领取与回写为短事务；重启后继续领取未完成任务。
- 导入原文、问题 CSV 与回执 PDF 内容保存在 PostgreSQL `extension_files`，下载经过账号、企业和代次验证。浏览器操作截图/运行摘要保存在 `var/rpa-runs/<company>/<generation>/<declaration>/`，该目录不静态公开；不保存 token 或浏览器网络 trace。
- 申报样例金额独立固定为销售额 `10000.00`、税额 `600.00`，不由账务摘要或票据推算。外部结果始终模拟。
- 企业恢复清理新增对象、文件、机器人证据并推进代次。文件清理失败保留 FAILED 恢复记录；同 key 可继续该恢复，未完成时拒绝新写入。
