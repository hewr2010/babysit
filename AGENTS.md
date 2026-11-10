# 宝宝成长日志

## 项目概述
微信小程序宝宝成长记录应用，使用 uni-app + Vue 3 + Pinia。后端沿用既有 Flask API，照片和视频由服务端提供缩略图、预览图、视频及原文件下载。

## 开发注意事项
1. 如果一个模块开始变得臃肿，主动拆分成子模块。
2. 不要输出多余的文档和报告；注释只解释不直观的逻辑，不留行末空白。
3. 测试代码放在 `tests/` 或 `frontend-mp/tests/`。
4. 修改小程序后必须构建，并使用微信开发者工具 CLI 自动操作和截图验证。
5. 验证后删除临时截图、日志等文件，关闭测试服务和开发者工具进程。
6. 不提交真实 AppID、密钥、token 或宝宝数据。
7. 视觉风格与 `qqing.top` 保持一致：粉色渐变页头、浅粉背景、白色圆角卡片和玫红主色；交互优先采用小程序原生导航、弹层、ActionSheet、选择器及安全区。
8. 每次完成新功能并验证后，默认上传新体验版、提交代码并推送到当前远端分支，无需另行等待确认。

## 功能
- 姓名验证后进入，本地记住验证状态。
- 宝宝姓名、生日、性别展示与编辑，月龄精确到几个月几天。
- 身高（cm）和体重（kg）的最新摘要、折线图与添加，不展示逐条明细，暂不提供删除入口。体重界面统一使用 kg，后端 API 仍以 g 存储，录入和展示时自动换算。
- 按月浏览照片和视频，按拍摄日期分组；每日默认显示 6 项，可展开查看更多或收起。
- 照片和视频统一使用微信原生 `previewMedia`，单次最多传入 50 项，不额外干预循环播放。缩略图星标标识重要时刻，右上角 `···` 按钮打开查看/标记、转发小程序卡片和保存原文件操作层，长按为辅助入口。分享链接保留自定义预览页，原文件限制 50MB。
- 预览页可转发小程序卡片到微信群，接收人通过姓名验证后直达对应媒体。
- 重要时刻创建、删除、首页时间轴和按月管理。

## API 约定
- `GET/POST /api/baby`
- `GET/POST /api/growth`，`DELETE /api/growth/:id`
- `GET /api/album`，`GET /api/album/:year/:month`
- `GET /api/milestones`，`GET /api/milestones/:filename`
- `POST /api/milestones`，`DELETE /api/milestones/:id`
- `GET /thumb/:filename`，`GET /preview/:filename`
- `GET /video/:filename`，`GET /livp/:filename`
- `GET /api/download/:filename`

## 构建与部署
```bash
cd frontend-mp
npm install
npm run type-check
npm run build:mp-weixin
```

构建产物位于 `frontend-mp/dist/build/mp-weixin/`。默认 API 为 `https://qqing.top`，开发时可用 `VITE_API_HOST=http://127.0.0.1:18080` 覆盖。

发布前在 `src/manifest.json` 的 `appid` 和 `mp-weixin.appid` 填入自己的 AppID，并在微信公众平台配置 `https://qqing.top` 为 request 和 downloadFile 合法域名。真实 AppID 不要提交到仓库。

## 自动化验证
1. 在 `frontend-mp/` 运行 `npm test` 和 `npm run type-check`。
2. 微信开发者工具「设置 > 安全」开启服务端口，运行 `npm run verify`。
3. 脚本会启动隔离的模拟 API、构建小程序、启动开发者工具，验证授权、资料编辑、成长添加/删除、月份切换、媒体预览、时刻创建/删除，并输出临时截图。
4. 截图默认写入系统临时目录，脚本退出时关闭模拟服务和开发者工具。需要保留截图检查时设置 `KEEP_SCREENSHOTS=1`，检查后手动删除目录。
5. 可用 `python3 tests/verify_h5.py` 做 Playwright 辅助截图验证。若本机没有屏幕捕获权限，微信脚本可设置 `ALLOW_SCREENSHOT_FAILURE=1` 仅跳过截图，功能断言不会跳过，交付时必须明确说明这一限制。
6. 正式 API 实装使用 `node tests/verify-production.js`，只执行只读浏览，不做增删改。自动启动器失效时，先用开发者工具 CLI 的 `auto --auto-port 9420` 开启项目自动化，再设置 `WS_ENDPOINT=ws://127.0.0.1:9420` 运行脚本。

## 小程序注意事项
- 自定义导航页面必须根据 `statusBarHeight` 留出顶部空间。
- 组件内旧版 canvas 必须向 `uni.createCanvasContext` 传入组件实例。
- WXSS 不使用 `*` 通配符，不混用不兼容的 `calc()` 单位。
- 自动化清理 storage 使用 `wx.clearStorageSync()`。
- 微信 `onLoad` 查询参数可能仍是 URL 编码，媒体文件名比较前必须安全解码；H5 与微信行为不同，分享测试需覆盖 `%20` 和非首项。
