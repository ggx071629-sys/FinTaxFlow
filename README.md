# FinTaxFlow

FinTaxFlow（财税云）是一个面向企业老板的财税工作台 Demo，支持 H5 和微信小程序。它把票据查询、模拟开票、CSV 导入、简单对账和模拟申报串成完整业务流程，适合本地演示和继续开发。

项目使用 UniApp / Vue 3 / TypeScript、FastAPI 和 PostgreSQL。登录鉴权、数据持久化、文件处理和浏览器自动化真实运行；开票与报税结果为模拟数据，不连接真实税务平台。

## 当前功能

业务重点是开票管理、导入与对账、模拟申报与恢复。H5 和微信小程序共用后端、账号和企业数据。

- **企业工作台**：切换企业，查看票据、报税和任务进度；账号与企业之间的数据隔离。
- **单笔与批量开票**：填写申请或导入固定 CSV 模板，复核后提交；支持失败重试、票据查询和 PDF 查看。
- **数据校验与对账**：显示导入文件的错误行、重复行和问题清单；按业务单号一对一匹配银行流水与账款记录，保留双方来源。
- **模拟申报**：Python 驱动 Chrome 操作本地模拟站点，记录执行过程，生成回执；中断后先核对受理记录再恢复，避免重复提交。
- **演示控制**：设置开票失败、申报回执中断等场景，或恢复当前企业的演示数据。
- **双端欢迎体验**：冷启动显示水面欢迎页，开场结束后轻触进入；支持减少动态效果，应用内切页与前后台切换不会重复播放。

账务摘要使用独立预置数据，开票和对账不会自动记账。邮件投递、真实税务接入和线上部署不在当前实现范围内。

## 本地运行

### 环境准备

一键启动面向 macOS 本地开发环境，脚本兼容系统自带 Bash。运行前准备：

| 依赖 | 用途 |
| --- | --- |
| Docker Desktop，已启动 | 通过 Compose 运行 PostgreSQL 16 |
| Python 3.12+ | FastAPI 后端与浏览器自动化 |
| Node.js / npm | 前端开发与构建；本机版本 Node 24.19 / npm 11.17 |
| Google Chrome | 执行模拟申报时使用 |
| 微信开发者工具（可选） | 运行小程序端 |

默认使用 `5432`（PostgreSQL）、`8000`（API）、`5173`（H5）端口。使用 nvm 时先配置 `default` 版本；双击入口在找不到 Node 时会尝试加载该版本。Docker CLI 支持 Docker Desktop 的 `~/.docker/bin` 路径。

### 启动项目

在项目根目录执行：

```sh
./start.sh --check   # 检查环境，不安装依赖、不启动服务、不修改数据库
./start.sh
```

也可以双击 `启动项目.command`。终端、npm 和 Make 入口使用同一套脚本：

| 操作 | npm 命令 | Make 命令 |
| --- | --- | --- |
| 启动完整项目 | `npm start` | `make start` |
| 只检查环境 | `npm run start:check` | `make check` |
| 启动但不打开浏览器 | `npm start -- --no-open` | `make start ARGS=--no-open` |
| 强制重新安装前后端依赖并启动 | `npm start -- --install-deps` | `make start ARGS=--install-deps` |
| 停止 API 与 H5 | `npm stop` | `make stop` |
| 同时停止数据库，保留数据卷 | `npm run stop:all` | `make stop-all` |

`./start.sh --help` 查看参数；`--no-open` 和 `--install-deps` 可以组合使用。根目录 npm 命令仅作入口，前端依赖仍安装在 `frontend/`。

启动依次执行：

1. 检查运行工具、Docker 连接、Compose 配置及应用端口。
2. 启动 PostgreSQL 并等待就绪。
3. 准备 `backend/.venv`，安装必要依赖，执行 Alembic 增量迁移和种子初始化。
4. 准备前端依赖与缺失配置，启动 API 和 H5；两端响应后打开浏览器。

首次使用新版脚本会安装前后端依赖并记录依赖文件校验值；后续未变化时跳过安装。`backend/pyproject.toml` 或前端 `package.json` / `package-lock.json` 变化时自动重新安装相应依赖，也可用 `--install-deps` 修复本地依赖环境。首次运行需要网络访问包源。

已有 `.env` 配置不会覆盖；启动会对配置所指向的数据库执行迁移，并补齐演示账号、企业及缺失的种子数据，不执行企业恢复或清库。日常演示应使用本地演示库。

启动后保持终端打开。重复启动会检查进程记录与两端响应；即使记录丢失，也会根据工作目录、可执行程序及本项目启动命令核实 API 和 H5，确认两端正常后恢复记录并打开已有服务，不会重复启动。进程时间统一使用固定语言和 UTC，中文终端与其他时区终端可共用记录。

若只剩本项目单独运行的 UniApp H5，脚本会核实身份后重启该前端并统一管理；`--check` 只检查，不恢复记录或停止进程。其他端口占用仍会报错。任一应用进程退出时，启动脚本会清理本次启动的另一端，并提示日志位置。

| 入口 | 地址 |
| --- | --- |
| H5 工作台 | [http://127.0.0.1:5173](http://127.0.0.1:5173) |
| API 文档（Swagger UI） | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |
| API 健康检查 | [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health) |

演示账号为 `demo_boss01` 和 `demo_boss02`，密码均为 `123456`，每个账号关联两家企业。

在启动终端按 `Ctrl+C` 停止 API 和前端，或从另一个终端执行：

```sh
make stop       # 停止 API 和 H5，保留数据库运行
make stop-all   # 同时停止 PostgreSQL 容器，保留数据卷
```

也可双击 `停止项目.command`。停止命令优先处理进程启动时间匹配的记录；记录丢失或格式过期时，会核实当前端口上的本项目服务及其启动主进程，恢复记录后停止。无法确认身份的其他服务不会被结束。停止应用或启动失败都不会自动停止数据库。

### 运行微信小程序

先启动上述后端服务，再从项目根目录构建：

```sh
npm --prefix frontend run build:mp-weixin
```

在微信开发者工具中导入 `frontend/dist/build/mp-weixin`，选择“不使用云服务”，按自己的测试号配置 AppID。本地联调使用 HTTP 地址，工具内需开启“不校验合法域名”选项。

小程序与 H5 共用同一套 API 和数据库。开发者工具不支持 CSV 文件分享时，页面提供“复制内容”出口，可将下载内容另存为 UTF-8 CSV；票据和回执可打开真实 PDF 文件。

需要修改后持续编译时，在后端已运行的情况下执行 `npm --prefix frontend run dev:mp-weixin`，导入 `frontend/dist/dev/mp-weixin`。一键启动默认只运行 H5，不自动构建或打开微信开发者工具。

## 先跑一条业务流程

登录并选择企业后，从首页进入“批量模拟开票”，上传 [billing-20.csv](backend/samples/billing-20.csv)。在尚未受理这些业务号的企业中，校验结果应为 **17 行有效、2 行错误、1 行重复**。复核有效行后提交，可在批次详情查看进度，再进入票据及 PDF。

如需演示部分失败，提交前在“演示设置”中选择下一次开票失败；批次完成后仅重试失败项。重复导入已受理的业务号会被识别为重复。

对账样例和格式说明见 [CSV 样例](backend/samples/README.md)。恢复当前企业会清除该企业新增业务和文件，请在需要重置演示时使用。

## 代码结构

```text
frontend/
├── src/pages/          # 工作台、票据、开票、对账、申报和任务页面
├── src/components/     # 共用界面组件
├── src/api/            # 按业务组织的 API 调用
├── src/http/           # 请求、鉴权与错误处理
├── src/stores/         # 登录会话与当前企业
└── portal/             # 供 Python 浏览器操作的本地模拟申报站点
backend/
├── app/api/            # HTTP 路由与访问授权
├── app/models/         # SQLAlchemy 数据模型
├── app/schemas/        # Pydantic 请求与响应定义
├── app/services/       # 开票、导入、对账、申报、文件与数据恢复
├── app/workers/        # 本地任务处理器
├── migrations/         # Alembic 数据库迁移
└── samples/            # 固定 CSV 模板样例
scripts/                # 项目启动、停止脚本
var/                    # 运行日志、进程信息、PDF 和机器人执行记录
```

前端通过 FastAPI 读写业务数据，任务状态保存在 PostgreSQL。后台处理器随 API 进程启动，前端轮询查询进度；模拟申报由处理器调用 Python Playwright，实际操作后端挂载的本地网页。当前实现不需要 Redis、Celery 或独立任务服务。

修改接口时，同时核对 [API 契约](frontend/API_CONTRACT.md)与 `frontend/src/types/api.ts`。修改数据结构时添加 Alembic 迁移；单独启动后端的步骤见 [后端开发说明](backend/README.md)。

## 配置与日常开发

一键脚本只在配置文件不存在时复制示例，已有配置不会被覆盖。

| 文件 | 常用配置 |
| --- | --- |
| `frontend/.env.local` | `VITE_API_BASE_URL`：API 基址，默认 `http://127.0.0.1:8000/api` |
| `backend/.env` | `DATABASE_URL`、`JWT_SECRET`、`CORS_ORIGINS` |
| `backend/.env` | `SIMULATION_BASE_URL`：机器人访问的后端地址；`RPA_BROWSER_CHANNEL` 默认 `chrome` |
| `compose.yaml` | 本地 PostgreSQL 的端口、账号与持久化数据卷 |

前端日常命令，均在项目根目录执行：

```sh
npm --prefix frontend run dev:h5            # 单独启动前端，需已有 API
npm --prefix frontend run type-check
npm --prefix frontend run build:h5          # 输出 frontend/dist/build/h5
npm --prefix frontend run build:mp-weixin   # 输出 frontend/dist/build/mp-weixin
```

一键启动运行期间无需再启动第二个 `dev:h5`。更新依赖文件后重新启动即可同步安装；单独开发前端时，在 `frontend/` 执行 `npm ci`。

模拟申报页面由 FastAPI 直接挂载 `frontend/portal/`，正常运行无需另开 `8780` 服务，也无需执行 `build:portal`。浏览器与 Python Playwright 只在申报任务执行时使用；一键启动不会下载 Chrome。

## 日志与排错

```sh
tail -f var/logs/backend.log var/logs/frontend.log
docker compose logs --tail=100 postgres
```

应用日志按次追加时间分隔，不覆盖之前的日志；依赖安装与迁移输出显示在启动终端。进程记录和启动锁位于 `var/run/`，PDF 与机器人证据位于 `var/invoice-pdfs/`、`var/rpa-runs/`，实际位置可由后端配置覆盖。

| 现象 | 处理 |
| --- | --- |
| Docker 无法连接 | 打开 Docker Desktop，等待引擎启动；检查当前终端是否有访问 Docker 的权限。 |
| 8000 / 5173 被占用 | 新版脚本启动的服务用 `npm stop` 停止。单独运行的本项目 UniApp H5 经身份核实后，下一次启动会自动重启；其他服务或无法核实的进程需回原终端停止。 |
| PostgreSQL 启动失败 | 检查 `docker compose logs postgres` 和 5432 端口；自检不会启动数据库或验证实际数据库连接。 |
| 提示已有启动会话或遗留锁 | 先 `npm stop`；确认原启动终端及初始化命令均已结束，且应用端口不再占用后，执行 `rmdir var/run/start.lock` 删除遗留空锁目录。 |
| 依赖损坏或模块缺失 | 停止项目后执行 `./start.sh --install-deps`；虚拟环境 Python 太旧时，移走 `backend/.venv` 后重建。 |
| 前端无法连接 API | 访问健康检查，核对 `VITE_API_BASE_URL`；更换前端地址时同步 `CORS_ORIGINS`。 |
| 模拟申报失败 | 确认 Chrome 和 `RPA_BROWSER_CHANNEL`，查看后端日志与机器人执行记录；修复后从原任务恢复，由后端先核对受理记录。 |
| CSV 校验不通过 | 使用固定模板与 UTF-8 编码；列名、列序和所选期间须匹配，示例对账文件固定为 `2026-09`。 |

`--check` 通过只说明基础环境检查通过，不代表数据库迁移、业务流程或 RPA 验收通过。当前配置与脚本面向本机开发；自定义 API 端口时需同时调整启动脚本、前端 API 地址及后端 `SIMULATION_BASE_URL`。

## 进一步阅读

- [前端开发说明](frontend/README.md) / [后端开发说明](backend/README.md)：分别运行、配置与调试。
- [API 契约](frontend/API_CONTRACT.md)：请求、响应、幂等、文件与企业隔离约定。
