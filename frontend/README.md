# FinTaxFlow 前端

UniApp + Vue 3 + TypeScript，支持 H5 和微信小程序，业务数据通过 FastAPI 读写。完整启动步骤见[项目说明](../README.md)，接口见 [API 契约](API_CONTRACT.md)。

## 本地开发

先启动 PostgreSQL 与[后端服务](../backend/README.md)，然后在本目录执行：

```sh
npm ci
cp .env.example .env.local
npm run dev:h5
```

已有 `.env.local` 时保留原配置。`VITE_API_BASE_URL` 默认为 `http://127.0.0.1:8000/api`；H5 地址为 `http://127.0.0.1:5173`。

整仓启动可在项目根目录运行 `./start.sh`，该入口自动准备配置与依赖。

## 构建

```sh
npm run type-check
npm run build:h5
npm run build:mp-weixin
npm run build:portal
```

H5 输出为 `dist/build/h5`。微信开发者工具导入 `dist/build/mp-weixin`，选择“不使用云服务”，在 `src/manifest.json` 配置自己的 AppID 或开发者工具测试号；本地 HTTP 联调需开启“不校验合法域名”。当前 AppID 仅为开发演示配置。

`build:portal` 将模拟申报页面和所需图片输出到 `dist/portal/`，仅用于静态预览。正常业务运行由 FastAPI 直接挂载 `portal/` 到 `/simulation-portal/`，无需另开静态服务器或构建该目录。机器人通过专用短期凭证调用同源接口。

## 代码结构

- `src/pages/`：登录、企业选择、工作台、票据、开票、对账、模拟申报、任务和演示设置；路由见 `src/pages.json`。
- `src/components/`、`src/styles/`：共享组件与样式。
- `src/api/`、`src/http/`、`src/types/`：业务请求、鉴权、错误处理与类型。
- `src/stores/`：登录会话和当前企业。
- `src/composables/`、`src/utils/`：页面状态、格式化、文件和表单处理。
- `src/static/`：图标与品牌图片。
- `src/welcome/`：H5 与小程序欢迎体验、动画生命周期和降级处理。
- `portal/`：本地模拟申报站点。

H5 和小程序共用后端。微信工具不支持 CSV 分享时可复制已下载的内容；PDF 使用原生文件预览。批次失败申请回到原批次重试，模拟申报恢复先核对后端受理记录。

欢迎体验在冷启动播放，支持减少动态效果，后台暂停；页面切换不重复播放。H5 使用独立欢迎层，小程序使用欢迎页面，WebGL 不可用时降级。

开票与税务结果均为模拟，账务摘要为预置数据；产品没有真实税务平台接入。
