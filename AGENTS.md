# 宝宝成长日志

## 项目概述
一个简洁美观的宝宝成长记录应用，使用 Vue3 + Flask 构建。照片和视频存储在百度网盘，应用本身只存储元数据和缓存缩略图。

当前同时维护两个前端：
- **H5 网页版**：`frontend/`，用于浏览器访问
- **微信小程序版**：`frontend-mp/`，使用 uni-app 跨端编译

## 开发注意事项
1. python 环境在 .venv 里
2. 如果一个模块开始变得臃肿了，需要主动地拆分成子模块
3. 不要输出多余的 md 和报告，注释只在刁钻的逻辑处再加，不要保留行末多余空白字符
4. 测试代码都放在 tests 文件夹
5. 每次开发完毕，都需要使用 playwright 打开浏览器验证 H5 功能；修改小程序则需要用微信开发者工具 CLI 自动截图验证
6. 测试完毕，需要把你测试用的无关紧要的文件删一删，进程回收一下
7. **响应式样式兼容性**：调整样式时必须同时检查移动端和 PC 端（`@media (min-width: 768px)`），确保两边边距、padding 等对齐一致
8. **CSS 对齐调试经验**：
   - "对齐"指的是视觉边界对齐，不是代码里的 padding/margin 数值相同
   - 调试时用 Playwright 的 `bounding_box()` 或小程序截图后测量实际渲染尺寸，别凭感觉调
   - 搞清楚组件层级关系（容器 vs 内容区），不同层级的 max-width/padding 会互相影响
   - 响应式样式要两端都截图验证，别只看一端

## 访问密码
前端访问密码：`何与青`（存储在 `frontend/src/components/AuthGuard.vue` 和 `frontend-mp/src/pages/auth/auth.vue`）

## 技术栈

### 后端 (babysit/)
- **Flask** - Web 框架
- **SQLite** - 数据库 (WAL 模式)
- **Pillow** - 图片处理
- **bypy** - 百度网盘 API 交互

### H5 前端 (frontend/src/)
- **Vue 3** - 框架
- **Vue Router** - 路由
- **Pinia** - 状态管理
- **Dayjs** - 日期处理
- **ECharts** - 图表（成长曲线）
- **Vite** - 构建工具

### 小程序前端 (frontend-mp/src/)
- **uni-app (Vue3)** - 跨端框架
- **Pinia** - 状态管理
- **Dayjs** - 日期处理
- 自定义 canvas 绘制成长曲线

## 项目结构

```
babysit/
├── app.py          # Flask 应用主入口，API 路由
├── db.py           # 数据库操作
├── baidu.py        # 百度网盘交互
├── config.py       # 配置
├── refresh_media.py # 后台媒体刷新进程
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

frontend-mp/src/
├── pages/          # 小程序页面
│   ├── auth/auth.vue
│   ├── index/index.vue
│   ├── video/video.vue
│   └── milestones/manage.vue
├── components/     # 复用组件
│   ├── Header.vue
│   ├── GrowthSection.vue
│   ├── PhotoSection.vue
│   ├── LineChart.vue
│   └── ...
├── stores/         # Pinia stores
├── shared/         # 与 H5 共享的业务逻辑
└── platform.ts     # 平台适配层（请求/存储/路由）
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

### 文件缓存
- `babysit/data/cache/thumbs/` - 200x200 缩略图
- `babysit/data/cache/previews/` - 800x800 预览图
- `babysit/data/cache/videos/` - 视频缓存（从 .livp 提取）

## 路由结构

### H5
| 路由 | 组件 | 说明 |
|------|------|------|
| `/` | HomeView | 首页（默认当前月份）|
| `/:year/:month` | HomeView | 指定月份的相册 |
| `/milestones/manage` | MilestoneManageView | 重要时刻管理后台 |
| `/p/:filename` | PhotoDirectView | 直接查看某张照片（分享链接）|

### 小程序
| 页面 | 说明 |
|------|------|
| `pages/auth/auth` | 授权页 |
| `pages/index/index` | 首页（成长曲线 + 时刻 + 相册）|
| `pages/video/video` | 视频播放页 |
| `pages/milestones/manage` | 重要时刻管理 |

## 主要功能模块

### 1. 宝宝信息
- 显示姓名、生日、月龄自动计算
- 支持修改宝宝信息

### 2. 成长曲线
- 身高/体重记录
- H5 使用 ECharts 图表
- 小程序使用自定义 canvas 折线图
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

`refresh_media.py` - 独立进程，每 3 分钟运行：
1. 从百度网盘获取文件列表
2. 生成缩略图和预览图
3. 提取 .livp 视频
4. 更新数据库

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

### H5
1. 后端开发：修改 `babysit/*.py`
2. 前端开发：修改 `frontend/src/**/*.vue` 或 `*.js`
3. 构建：`cd frontend && npm run build`
4. 测试：`python -m babysit.app` + Playwright

### 微信小程序
1. 开发：`frontend-mp/src/**/*.vue` 或 `*.ts`
2. 配置 AppID：编辑 `frontend-mp/src/manifest.json`，把 `appid` 和 `mp-weixin.appid` 填成你自己的微信小程序 AppID（仓库里留空，不提交真实 ID）
3. 构建：`cd frontend-mp && npm run build:mp-weixin`
4. 产物在 `frontend-mp/dist/build/mp-weixin/`
5. 自动化验证：`node frontend-mp/scripts/screenshot.js`

## 小程序验证指南

### 前置准备
- 安装微信开发者工具（macOS 默认路径 `/Applications/wechatwebdevtools.app`）
- 在开发者工具里打开"设置 > 安全"，开启服务端口
- 导入项目时勾选"不校验合法域名..."

### 自动化截图脚本
`frontend-mp/scripts/screenshot.js` 基于 `miniprogram-automator`，会自动：
1. 启动微信开发者工具并加载 `dist/build/mp-weixin`
2. 清空本地 storage，进入授权页截图
3. 模拟授权后进入首页截图
4. 进入视频页验证返回按钮截图
5. 关闭开发者工具

运行：
```bash
cd frontend-mp
npm run build:mp-weixin
node scripts/screenshot.js
```

截图会临时生成在项目根目录，验证后应及时删除。

### 小程序常见坑
- **自定义导航栏**：`navigationStyle: "custom"` 的页面必须自己用 JS 读取 `statusBarHeight` 留出状态栏高度，否则内容会被系统状态栏遮挡。
- **canvas 组件**：在组件内使用 canvas 时，`uni.createCanvasContext('id')` 需要传入组件实例（`getCurrentInstance().proxy`），否则在微信里画不上。
- **WXSS 限制**：不支持 `*` 通配符选择器，不支持 `calc()` 里混用 `rpx` 与 `px`（建议用 JS 动态计算 px 值）。
- **storage 清理**：自动化测试里要用 `wx.clearStorageSync()` 而不是 `uni.clearStorageSync()` 才能清干净。
- **事件未绑定**：按钮点了没反应，先检查父组件是否真的监听了对应事件。

## 小程序部署流程

1. 注册 [微信公众平台](https://mp.weixin.qq.com) 小程序账号，拿到 AppID
2. 把 `frontend-mp/src/manifest.json` 里的 `appid` 和 `mp-weixin.appid` 填成你的 AppID
3. 微信公众平台「开发管理 → 开发设置」配置合法域名：
   - `request合法域名`：`https://qqing.top`
   - `downloadFile合法域名`：`https://qqing.top`
4. 构建：`cd frontend-mp && npm run build:mp-weixin`
5. 微信开发者工具导入 `frontend-mp/dist/build/mp-weixin`
6. 开发者工具点击「上传」，填写版本号和备注
7. 微信公众平台「版本管理」里设为「体验版」扫码真机测试，或提交审核后发布

**注意**：代码里不要提交真实的 AppID、密钥、token 等敏感信息。`manifest.json` 里的 AppID 在本地开发/上传前再填。
