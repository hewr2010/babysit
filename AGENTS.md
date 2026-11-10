# 宝宝成长日志

## 项目概述
一个简洁美观的宝宝成长记录应用，使用 Vue3 + Flask 构建。照片和视频存储在百度网盘，应用本身只存储元数据和缓存缩略图。

同时提供 H5 网页版和 uni-app 微信小程序版，小程序代码位于 `frontend-mp/`。

## 开发注意事项
1. python 环境在 .venv 里
2. 如果一个模块开始变得臃肿了，需要主动地拆分成子模块
3. 不要输出多余的 md 和报告，注释只在刁钻的逻辑处再加，不要保留行末多余空白字符
4. 测试代码都放在 tests 文件夹
5. 每次开发完毕，都需要使用 playwright 打开浏览器验证功能。确认你写的功能都通过测试了，再移交给用户
6. 测试完毕，需要把你测试用的无关紧要的文件删一删，进程回收一下
7. **响应式样式兼容性**：调整样式时必须同时检查移动端和 PC 端（`@media (min-width: 768px)`），确保两边边距、padding 等对齐一致
8. **CSS 对齐调试经验**：
   - "对齐"指的是视觉边界对齐，不是代码里的 padding/margin 数值相同
   - 调试时用 Playwright 的 `bounding_box()` 测量实际渲染尺寸，别凭感觉调
   - 搞清楚组件层级关系（容器 vs 内容区），不同层级的 max-width/padding 会互相影响
   - 响应式样式要两端都截图验证，别只看一端

## 访问密码
前端访问密码：`何与青`（存储在 `frontend/src/components/AuthGuard.vue`）

## 技术栈

### 后端 (babysit/)
- **Flask** - Web 框架
- **SQLite** - 数据库 (WAL 模式)
- **Pillow** - 图片处理
- **bypy** - 百度网盘 API 交互
- **InsightFace**（可选）- 本地人脸检测与特征比对

### 前端 (frontend/src/)
- **Vue 3** - 框架
- **Vue Router** - 路由
- **Pinia** - 状态管理
- **Dayjs** - 日期处理
- **ECharts** - 图表（成长曲线）
- **Vite** - 构建工具

## 项目结构

```
babysit/
├── app.py          # Flask 应用主入口，API 路由
├── db.py           # 数据库操作
├── baidu.py        # 百度网盘交互
├── config.py       # 配置
├── refresh_media.py # 后台媒体刷新进程
├── photo_sync.py   # 手机照片自动筛选 CLI 与同步流程
├── photo_sync_config.py # 照片同步环境配置
├── photo_sync_db.py # 照片同步状态与去重
├── face_matcher.py # 本地人脸识别
├── video_frames.py # 视频解包、抽帧与缓存
├── photo_sync_bmk.py # 本地照片视频识别回归 benchmark
├── baidu_sync.py   # 百度图片列表与网盘内复制
└── utils.py        # 工具函数

frontend/src/
├── router/         # Vue Router 配置
├── stores/         # Pinia stores
│   ├── app.js      # 主应用状态
│   └── modal.js    # 弹窗状态
├── components/     # 组件
│   ├── Header.vue
│   ├── GrowthSection.vue
│   ├── PhotoSection.vue
│   ├── MilestoneTimeline.vue
│   ├── PhotoViewer.vue
│   └── ...
└── views/          # 页面级组件
    ├── HomeView.vue
    ├── MilestoneManageView.vue
    └── PhotoDirectView.vue
```

## 数据存储

### SQLite 数据库表

**baby** - 宝宝信息
- id, name, birthday, gender

**growth** - 成长记录（身高/体重）
- id, date, metric_type, value

**media_files** - 媒体文件元数据
- id, filename, file_type, file_size, md5, date, time, processed

**milestones** - 重要时刻
- id, media_filename, title, description

**photo_sync_items** - 手机照片同步状态（可选照片筛选进程）
- fs_id, source_path, filename, md5, size, server_mtime
- thumbnail_path, face_score, face_count, status, target_path
- error, retry_count, created_at, updated_at

### 文件缓存
- `babysit/data/cache/thumbs/` - 200x200 缩略图
- `babysit/data/cache/previews/` - 800x800 预览图
- `babysit/data/cache/videos/` - 视频缓存（从 .livp 提取）

## 路由结构

| 路由 | 组件 | 说明 |
|------|------|------|
| `/` | HomeView | 首页（默认当前月份）|
| `/:year/:month` | HomeView | 指定月份的相册 |
| `/milestones/manage` | MilestoneManageView | 重要时刻管理后台 |
| `/p/:filename` | PhotoDirectView | 直接查看某张照片（分享链接）|

## 主要功能模块

### 1. 宝宝信息
- 显示姓名、生日、月龄自动计算
- 支持修改宝宝信息

### 2. 成长曲线
- 身高/体重记录
- ECharts 图表展示趋势
- 支持添加新记录

### 3. 重要时刻 (Milestones)
- 在照片查看器中标记重要时刻
- 主页时间轴展示所有时刻
- 管理后台批量管理
- 分享链接直达照片

### 4. 相册
- 按月展示照片
- 支持照片/视频预览
- 原图下载（50MB 限制）
- .livp 格式自动提取视频

## 后台进程

`refresh_media.py` 每 3 分钟从正式相册获取文件，生成缩略图、预览图、提取 Live Photo 视频并更新 `media_files`。它只负责展示，不负责判断照片中是否有女儿。全量补历史缓存可能很慢，调试单个文件时优先调用 `process_media_file()`，不要无必要地全量刷新。

## 照片同步方案（当前实现）

### 1. 总体链路和目录

```text
两台 iPhone → /来自：iPhone
  → 官方 imagelist 增量读取元数据/缩略图
  → 本地 InsightFace 人脸及分块识别
  → 高分复制到 /apps/bypy/爸妈与小宝
  → 灰区复制到 /apps/bypy/爸妈与小宝-review 并发送 Bark
  → refresh_media.py 负责展示缓存和 media_files 入库
```

- 正式目录：`/apps/bypy/爸妈与小宝`
- 人工灰区：`/apps/bypy/爸妈与小宝-review`
- 来源文件只复制，不移动、不删除。
- 手机自动备份目的地是固定的，不能改为 bypy 应用目录。官方 `filemanager` 和下载接口也只允许 `/apps/{appname}`，所以读取元数据用官方 API，跨目录复制/下载用 BaiduPCS-Go。
- bypy CLI 自身限制在 `/apps/bypy`，但现有 OAuth token 的 `imagelist` 可以读取 `/来自：iPhone`，这是已验证行为，不要误判为 token 无效。

### 2. 授权与秘密信息

- 官方列表、元数据、缩略图：`babysit/baidu.py:get_access_token()` 复用 `~/.bypy/bypy.json`，也可用 `BABYSIT_BAIDU_ACCESS_TOKEN` 覆盖。
- 全网盘复制和下载：BaiduPCS-Go，配置目录固定在 `babysit/data/photo_sync/baidupcs-config`。
- `BaiduPCS-Go who` 返回 `uid: 0` 也代表未登录，不能只看退出码。配置目录不一致会出现“一个命令已登录、另一个命令 user not exists”，所有调用必须统一配置目录。
- 首次登录可通过 WebBridge 复用浏览器现有百度会话，完成后关闭标签组和网络捕获。不要打印、提交或临时保存 Cookie。
- 不读取、不依赖生产环境数据库。本地 DB 不完整时，以网盘目标目录对账为准。
- Bark URL 不进 Git。可用 `BARK_URLS` 逗号分隔，或被忽略的 `babysit/data/photo_sync/bark-urls.txt`（每行一个 URL，也可指定 `BARK_URLS_FILE`）。`BARK_KEY`/`~/.zshrc` 仅作回退。

### 3. 增量、去重和两台 iPhone

每轮先做目标目录对账，再做识别：

- `fs_id` 是主键，文件名只用于展示，不能单独作为去重依据。
- 同名且 MD5 一致：视为已处理。
- 同名但 MD5 不同：不是同一文件，继续识别，目标文件名添加 `_fs_id` 后缀，避免两台设备互相覆盖。
- 已带对应 `_fs_id` 后缀的文件：视为已处理。
- 任意目标文件与来源 MD5 相同：即使改名也视为已处理。
- 本轮复制成功后立即更新内存中的目标索引，避免同轮重复复制。
- 复制前先持久化 `target_path`，崩溃后复用同一路径；只有网盘目标校验成功才标记 `copied`。

分页和 backlog：

- `imagelist` 按修改时间倒序，默认每页 100、每轮最多识别 50 个新文件。
- `scan_backlog=0` 时，如果当前页全部已处理，可提前停止。
- 初次处理或重排历史时必须确保 `scan_backlog=1`，否则可能“requeue 了但根本扫不到旧文件”。有积压时每 60 秒一批，追平后恢复 1800 秒。
- `fs_id + MD5` 防止双设备、同名和延迟上传漏扫；不要只依赖文件名或拍摄日期。`server_mtime` 用于扫描，`local_mtime` 可能才是拍摄时间。

### 4. 状态机和失败恢复

`photo_sync_items` 保存 `fs_id/source_path/filename/md5/size/server_mtime/thumbnail_path/face_score/face_count/status/target_path/error/retry_count/timestamps`。

主要状态：

- `pending`：待识别。
- `matched`：已达到自动复制阈值，待复制。
- `copying`：复制中。
- `copied`：正式目录已存在或已复制成功。
- `rejected`：分数过低或无人脸，本轮不再处理。
- `review`：待人工确认，尚未归档。
- `review_copied`：已复制到灰区目录，不重复归档/通知。
- `error`：暂时性失败，默认最多重试 10 次，之后进入人工 review。
- `HANDLED_STATUSES = copied/rejected/review/review_copied`，这些不会被普通增量扫描重复分析。

下载与视频异常：

- 缩略图 4 路并发预取，单文件失败不影响整批。
- BaiduPCS-Go 可能退出码为 0 但返回 0B，必须校验目标文件非空并最多重试 3 次、指数退避。
- 损坏 zip、无视频流、ffprobe/ffmpeg 错误统一转为可重试错误，删除损坏原文件避免复用；不能让 daemon 退出。
- `CalledProcessError` 不属于普通 OSError，必须显式转换处理。

### 5. 人脸参考库与阈值

- 只使用**单人、清晰、近期**的宝宝照片。多人合照一律跳过，因为“取最大人脸”会把爸爸/妈妈特征训练进去，曾造成父母视频误复制。
- 新生儿和近月龄照片要同时保留，定期补充，避免年龄变化导致 recall 下降。
- 当前阈值：全图自动复制 `0.54`，人工灰区 `0.35`。灰区归档不影响自动复制阈值。
- `dry_run` 只做识别，不复制、不发 Bark；高分也进入 review 供检查。

不要通过全局降低阈值解决漏检。负样本里父母、舞台人物、包包和文字截图都曾被验证过，阈值和参考库必须一起评估。

### 6. 静态照片、视频和镜中脸

静态照片：

- 先全图识别；低置信度时做 2×2 重叠分块。
- 四个区域分别占原图 60%×60%，位置为 `(0,0)/(0.4,0)/(0,0.4)/(0.4,0.4)`，每块放大 2 倍。
- 分块自动复制阈值 `0.50`，用于镜中脸和远距离小脸。返回最佳分块路径供审核和展示。

视频：

- `.livp` 先按 zip 解出 `.mov`，不能只看封面。
- 时长 ≤4 秒时每 0.5 秒抽帧；更长视频至少每 2 秒一帧，最多覆盖 24 个时间点。
- 每帧使用全图+分块逻辑，取最高相似度及最佳帧。
- 实际很多 `.livp` 只有 1–3 秒，不要根据用户描述的时长猜实现，先 ffprobe 验证。

镜中脸已验证案例：`2026-11-08 181218.heic`。全图无人脸，分块后约 0.50，已能复制到正式目录。该案例必须保留在本地 benchmark 中，防止回退。

### 7. 灰区和人工处理

- `review` 项会复制到 `爸妈与小宝-review` 并变为 `review_copied`，随后发送汇总 Bark。
- 你手动删除灰区文件：不重新复制。
- 你手动复制到正式目录：下一轮对账会改为正式 `copied`。
- `approve <fs_id>` 也可复制到正式目录，`reject <fs_id>` 标记不匹配。
- 每轮只发有实际活动的汇总，空轮不发。内容包括新复制、目标已有、灰区新增、已归档、当前待人工处理、不匹配和失败数。
- 多个 Bark 地址独立请求，单个超时/失败不影响另一个，也不能阻断同步。
- 可用 Cron 定时检查 pending/backlog，完成后发送“存量处理完成”并删除监控任务，不要另开长期观察进程。

### 8. 已验证不能简单使用的方法

- **不要拼接很多图片缩小后做人脸识别**：推理不是主要瓶颈，且镜中脸/小脸会更难识别。
- **不要仅凭身体/衣服 ReID 自动复制**：遮脸测试不稳定，且包包也有人形高分，已验证并撤回。
- **不要把 body bbox 当有人就进灰区**：负样本误报明显。
- **不要依赖百度原生“宝宝”模糊标签**：覆盖不全；`unisearch` 也曾返回 params error，不能当唯一来源。
- **不要仅凭“处理过”就声称“找全了”**：必须看具体文件状态、实际目标路径和用户指出的漏检画面。

### 9. 性能与缓存

- 实测人脸推理约 0.187 秒/张，主要瓶颈是缩略图下载和等待，不是模型。
- 缩略图默认 4 路并发预取，避免共享 requests.Session 的线程安全问题。
- 复用已有缩略图和 `video_work/<fs_id>/frame-*.jpg`，重扫时不重复下载。
- 复制仍串行执行，防止并发复制冲突。
- 日志在 `babysit/data/photo_sync/daemon.log`，每张实际复制和每轮汇总都在同一进程里，无需额外观察进程。

### 10. Benchmark 与历史重扫

私人样本、原视频、帧和报告都放在被忽略的 `babysit/data/photo_sync_bmk/`，不进 Git。当前基线包含 12 个正例、18 个负例及镜中脸专项，历史最好成绩为正例全通过、负例零误报；修改参考库、分块或阈值后必须重新跑，不能引用旧结果。

```bash
.venv/bin/python -m babysit.photo_sync_bmk \
  --references babysit/data/photo_sync/references \
  --output babysit/data/photo_sync_bmk/report.json
```

历史算法变化后：

1. 暂停唯一的 `babysit:sync`。
2. 用 `requeue` 重排 `rejected/review`，可 `--videos-only` 或 `--status rejected`。
3. 对老文件确认 `scan_backlog=1`，再恢复同一个 daemon。
4. 等 pending/error 为 0、backlog 为 0 后再评估实际复制结果。

### 11. tmux 和常用操作

只允许一个 `babysit` session，任务以 window 形式存在；不要新建 `babysit-photo-*` 等 session。当前同步进程也只有一个，避免并发处理同一批文件。

```bash
.venv/bin/python -m babysit.photo_sync doctor
.venv/bin/python -m babysit.photo_sync sync --dry-run --limit 20
.venv/bin/python -m babysit.photo_sync status
.venv/bin/python -m babysit.photo_sync recent --hours 24 --limit 20
.venv/bin/python -m babysit.photo_sync sync-reviews
.venv/bin/python -m babysit.photo_sync requeue --videos-only

tail -f babysit/data/photo_sync/daemon.log
tmux attach -t babysit
```

## H5 查看器当前交互

- 未放大：左右翻页、下滑关闭。
- 双击放大/还原，双指 1–4 倍缩放，放大后单指拖动；桌面支持滚轮。
- 放大后上下关闭和左右翻页都被抑制，视频保留原生控件。
- 下滑返回必须跟随手势向下离场，而不是横向退出；相关测试在 `tests/test_iphone_photo_viewer.py`。

## API 端点

### 宝宝信息
- `GET/POST /api/baby`

### 成长记录
- `GET/POST /api/growth`
- `DELETE /api/growth/:id`

### 相册
- `GET /api/album` - 所有媒体
- `GET /api/album/:year/:month` - 按月筛选

### 重要时刻
- `GET /api/milestones` - 所有时刻
- `GET /api/milestones/:filename` - 某张照片的时刻
- `POST /api/milestones` - 创建时刻
- `DELETE /api/milestones/:id` - 删除时刻

### 媒体文件
- `GET /thumb/:filename` - 200x200 缩略图
- `GET /preview/:filename` - 800x800 预览图
- `GET /video/:filename` - 视频缓存
- `GET /livp/:filename` - 从 livp 提取的视频
- `GET /api/download/:filename` - 原文件下载（流式代理）

## 开发流程

1. 后端开发：修改 `babysit/*.py`
2. 前端开发：修改 `frontend/src/**/*.vue` 或 `*.js`
3. 构建：`cd frontend && npm run build`
4. 测试：`python -m babysit.app` + Playwright

## 微信小程序

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
