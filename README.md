# babysit - 宝宝成长管家

简洁美观的单页面宝宝成长记录应用。

开发请参照 [AGENTS.md](./AGENTS.md)

## 功能

- 👶 **宝宝信息** - 姓名、生日、月龄自动计算
- 📅 **日期切换** - 按日期查看和记录
- 📝 **生活记录** - 喂奶、睡眠、换尿布
- 📸 **每日相册** - 百度网盘照片按日期展示，显示拍摄时间
- 💉 **疫苗提醒** - 根据月龄自动提醒疫苗和体检
- 📊 **热力图** - 图标化显示每日记录，一目了然

## 安装

```bash
# 安装
uv pip install -e .

# 配置百度网盘
bypy info
```

## 使用

需要同时运行两个进程：

### 1. 启动主应用（Web 服务）

```bash
# 开发模式（单进程，有热重载）
python -m babysit.app

# 生产模式（多进程，更稳定）
gunicorn -w 2 -b 0.0.0.0:8080 "babysit.app:create_app()"

# 指定端口
PORT=9000 python -m babysit.app
gunicorn -w 2 -b 0.0.0.0:9000 "babysit.app:create_app()"
```

### 2. 启动后台媒体刷新进程（另一个终端）

```bash
python -m babysit.refresh_media
```

该进程每 3 分钟从百度网盘获取多媒体文件列表，并进行预处理（生成缩略图、预览图、提取视频等），只有完全完成预处理的文件才会在数据库中标记为可用。

### 3. 手机照片自动筛选（可选）

安装人脸识别依赖：

```bash
uv pip install -e '.[photo-sync]'
```

另外安装 [BaiduPCS-Go](https://github.com/qjfoidnh/BaiduPCS-Go)，按其 README 完成登录。项目会优先使用 `babysit/data/photo_sync/bin/BaiduPCS-Go`（若存在），否则从 PATH 查找。官方接口负责读取手机目录和缩略图，BaiduPCS-Go 负责把筛选出的原图复制到应用目录。登录凭证不要写入项目或提交到 Git。

登录时让凭证与同步进程使用同一个项目内配置目录：

```bash
export BAIDUPCS_GO_CONFIG_DIR="$PWD/babysit/data/photo_sync/baidupcs-config"
```

配置手机备份目录，并在本地参考目录放入女儿不同年龄、角度的清晰照片：

```bash
export PHOTO_SYNC_SOURCE_PATH="/来自：iPhone"
export PHOTO_SYNC_REFERENCE_DIR="$PWD/babysit/data/photo_sync/references"
```

先检查链路，再进行不复制文件的识别：

```bash
python -m babysit.photo_sync doctor
python -m babysit.photo_sync sync --dry-run --limit 20
python -m babysit.photo_sync status --status review
```

确认识别结果后，复制或跳过待确认项目：

```bash
python -m babysit.photo_sync approve <fs_id>
python -m babysit.photo_sync reject <fs_id>
```

正式执行一轮或持续运行：

```bash
python -m babysit.photo_sync sync
python -m babysit.photo_sync daemon
```

默认每 30 分钟处理最多 50 张新照片，相似度不低于 0.54 自动复制，0.35 到 0.54 进入人工确认。可分别通过 `PHOTO_SYNC_INTERVAL`、`PHOTO_SYNC_SCAN_LIMIT`、`PHOTO_SYNC_AUTO_THRESHOLD`、`PHOTO_SYNC_REVIEW_THRESHOLD` 调整。其他配置见 `babysit/photo_sync_config.py`。

每轮会先读取目标目录进行对账：同名且 MD5 一致的文件、带对应 `fs_id` 后缀的文件或 MD5 相同的文件都视为已经处理，不再运行人脸识别，也不占用每轮分析额度。两台 iPhone 产生同名但 MD5 不同的文件时不会跳过，而是添加 `fs_id` 后缀后复制。因此本地 SQLite 不是完整的处理历史也没关系，不需要读取其他环境的生产数据库。积压照片通过 `scan_backlog` 分批续跑，目标目录无法读取时会停止本轮以避免重复复制。

缩略图默认使用 4 路并发预取，可通过 `PHOTO_SYNC_DOWNLOAD_WORKERS` 调整（1 到 16）。存在积压时默认每 60 秒继续下一批，可通过 `PHOTO_SYNC_BACKLOG_INTERVAL` 调整；追平后恢复 `PHOTO_SYNC_INTERVAL` 指定的常规间隔。人脸识别和云端复制仍按顺序执行，不通过拼接缩小图片来牺牲小脸识别准确率。

`.livp`、`.mp4`、`.mov` 不再只分析网盘封面：同步进程会下载视频并抽帧，短视频约每 0.5 秒一帧，长视频最多覆盖 24 个时间点，使用最佳帧的人脸相似度。下载遇到 0B 或网络抖动会退避重试，抽帧结果会缓存复用。

#### 识别回归 benchmark 与历史重扫

私人样本和帧文件保存在被 Git 忽略的 `babysit/data/photo_sync_bmk/`，不会提交到仓库。运行回归：

```bash
python -m babysit.photo_sync_bmk \
  --references babysit/data/photo_sync/references \
  --output babysit/data/photo_sync_bmk/report.json
```

输出包括自动复制 recall、包含人工灰区的 recall，以及负样本误复制数。修改参考脸库或阈值后应重复运行。历史 `rejected/review` 可在停止同步进程后重新排队：

```bash
# 只重新识别视频
python -m babysit.photo_sync requeue --videos-only

# 重新识别静态照片和视频
python -m babysit.photo_sync requeue

# 只重新识别 rejected，保留已有 review 状态
python -m babysit.photo_sync requeue --status rejected
```

重排后重新运行 `python -m babysit.photo_sync daemon` 即可，已有缩略图和帧缓存会复用。

#### 使用 tmux 长期运行

在本机执行以下命令，后台持续识别 `/来自：iPhone` 并复制到 `/apps/bypy/爸妈与小宝`：

```bash
mkdir -p /Users/hwr/storage/babysit/babysit/data/photo_sync

tmux new-session -d -s babysit -n sync \
  "cd /Users/hwr/storage/babysit && \
   PHOTO_SYNC_SOURCE_PATH='/来自：iPhone' \
   BAIDUPCS_GO_CONFIG_DIR='/Users/hwr/storage/babysit/babysit/data/photo_sync/baidupcs-config' \
   PYTHONUNBUFFERED=1 \
   .venv/bin/python -m babysit.photo_sync daemon \
   >> babysit/data/photo_sync/daemon.log 2>&1"
```

所有任务只使用 `babysit` 这一个 session，其他任务以 window 形式加入。复制后的媒体还需要现有刷新进程生成缩略图、提取视频并入库，建议同时运行：

```bash
tmux new-window -t babysit -n refresh \
  "cd /Users/hwr/storage/babysit && \
   PYTHONUNBUFFERED=1 \
   .venv/bin/python -m babysit.refresh_media \
   >> babysit/data/photo_sync/refresh-media.log 2>&1"
```

常用管理命令：

```bash
# 查看 session 和窗口
tmux ls
tmux list-windows -t babysit

# 查看同步日志
tail -f /Users/hwr/storage/babysit/babysit/data/photo_sync/daemon.log

# 接入会话；Ctrl-b 再按 d 离开且不停止进程
tmux attach -t babysit
# Ctrl-b 再按 n / p 切换下一个 / 上一个 window

# 只停止指定任务
tmux kill-window -t babysit:sync
tmux kill-window -t babysit:refresh
```

#### 查看最近同步内容

不需要单独运行观察进程。同步进程会在每张文件实际复制并校验成功后，立即记录来源、目标和人脸相似度，并在每轮结束时记录汇总：

```text
2026-11-08 22:30:00 已复制：/来自：iPhone/IMG_0001.jpg -> /apps/bypy/爸妈与小宝/IMG_0001.jpg，相似度 0.812
2026-11-08 22:30:05 本轮：复制 1，目标已有 20，待确认 0，跳过不匹配 29，失败 0，已处理 100
```

直接查看同一个进程的日志：

```bash
tail -f /Users/hwr/storage/babysit/babysit/data/photo_sync/daemon.log
```

目标目录已有而跳过的文件不逐条打印，避免日志过多。也可以随时手动运行 `python -m babysit.photo_sync recent --hours 24 --limit 20` 查询最近记录，无需常驻另一个观察进程。

访问 http://localhost:8080

## 数据存储

所有数据存储在项目目录内：
- `babysit/data/babysit.db` - SQLite 数据库
- `babysit/data/cache/` - 百度网盘文件列表缓存

注：照片和视频直接使用百度网盘直链，无需本地存储。

## 配置

修改百度网盘路径：
```bash
export BABYSIT_PATH="/你的相册路径"
```

## 主题

应用采用温馨的公主粉配色，更适合记录女宝宝的成长。主要颜色：
- 主色：粉红色 (#ec4899)
- 背景：渐变粉色
- 图标：使用emoji表情，更生动可爱

## 界面

- 顶部：宝宝信息 + 月龄
- 昨日总结：显示昨天的睡眠/喂奶/换尿布统计
- 热力图：按月展示所有记录，图标化显示
- 成长记录：身高/体重/头围曲线
- 疫苗提醒：根据月龄显示近期疫苗和体检
- 相册：按月展示百度网盘照片，支持查看原图
- 快捷按钮：底部固定，快速记录喂奶/睡眠/换尿布/生长
