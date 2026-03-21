# 宝宝成长日志

## 项目概述
一个简洁美观的单页面宝宝成长记录应用，使用 Vue3 + Flask 构建。照片和视频存储在百度网盘，应用本身只存储元数据和缓存缩略图。

## 开发注意事项
1. python 环境在 .venv 里
2. 如果一个模块开始变得臃肿了，需要主动地拆分成子模块
3. 不要输出多余的 md 和报告，注释只在刁钻的逻辑处再加，不要保留行末多余空白字符
4. 测试代码都放在 tests 文件夹
5. 每次开发完毕，都需要使用 playwright 打开浏览器验证功能。确认你写的功能都通过测试了，再移交给用户
6. 测试完毕，需要把你测试用的无关紧要的文件删一删，进程回收一下

## 技术栈

### 后端 (babysit/)
- **Flask** - Web 框架
- **SQLite** - 数据库 (WAL 模式)
- **Pillow** - 图片处理
- **bypy** - 百度网盘 API 交互

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

1. 后端开发：修改 `babysit/*.py`
2. 前端开发：修改 `frontend/src/**/*.vue` 或 `*.js`
3. 构建：`cd frontend && npm run build`
4. 测试：`python -m babysit.app` + Playwright
