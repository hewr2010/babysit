# babysit

基于百度网盘的轻量级宝宝相册，**零存储、缩略图预览、即点即看**。

## 特点

- 📱 **手机友好**：自适应布局，支持触屏滑动浏览
- 📅 **按日期分组**：自动从文件名提取日期
- 🖼️ **缩略图预览**：自动生成 300x300 缩略图，快速浏览
- ☁️ **零存储原图**：点击时才从百度网盘加载原图/视频
- 🎬 **视频支持**：可播放 MP4 等格式
- 🔄 **实时刷新**：一键同步百度网盘最新文件

## 安装

```bash
# 克隆或下载代码
cd babysit

# 使用 uv 安装（推荐）
uv pip install -e .

# 或使用 pip
pip install -e .
```

## 配置

### 1. 百度网盘授权

```bash
# 安装 bypy
uv pip install bypy

# 授权
bypy info
```

按提示完成授权（会打开浏览器让你登录百度账号）。

### 2. 修改相册路径（可选）

默认相册路径是 `/爸妈与小宝`，可以通过环境变量修改：

```bash
export BABY_ALBUM_PATH="/你的相册路径"
```

## 使用

### 启动服务

```bash
# 方式 1: 直接运行 app.py
python babysit/app.py

# 方式 2: 使用模块方式
python -m babysit.app
```

访问 http://localhost:8080

### 生产环境部署

使用 gunicorn：

```bash
# 安装 gunicorn
uv pip install gunicorn

# 启动
gunicorn -w 2 -b 0.0.0.0:8080 "babysit.app:create_app()"

# 后台运行
nohup gunicorn -w 2 -b 0.0.0.0:8080 "babysit.app:create_app()" > app.log 2>&1 &
```

## 工作原理

```
页面加载
   ↓
显示缩略图（300x300，缓存到本地）
   ↓
用户点击
   ↓
从百度网盘获取临时直链（有效期约 8 小时）
   ↓
显示原图/播放视频
```

**优势：**
- ECS 上只缓存缩略图（约 10-50KB/张），节省空间
- 原图/视频直接从百度网盘加载，不占 ECS 带宽

## 部署到 ECS

### 1. 上传代码

```bash
rsync -avz --exclude='.venv' --exclude='.git' \
  ./ root@your-ecs-ip:/opt/babysit/
```

### 2. 在 ECS 上安装

```bash
ssh root@your-ecs-ip
cd /opt/babysit
uv pip install -e .
```

### 3. 配置百度网盘

```bash
bypy info
```

### 4. 启动服务

```bash
python babysit/app.py
```

或生产模式：

```bash
gunicorn -w 2 -b 0.0.0.0:8080 "babysit.app:create_app()"
```

### 5. 配置 Nginx（可选）

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 6. 设置开机自启（systemd）

创建 `/etc/systemd/system/babysit.service`：

```ini
[Unit]
Description=Babysit
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/babysit
ExecStart=/usr/bin/python3 babysit/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启用：
```bash
systemctl enable babysit
systemctl start babysit
```

## 手机访问

确保手机和 ECS 在同一网络或 ECS 有公网 IP：

```
http://<ECS-IP>:8080
```

## 数据目录

缩略图和索引缓存存储在用户主目录：

```
~/.babysit/
├── cache/          # 文件索引
└── thumbnails/     # 缩略图缓存（300x300 JPEG）
```

## 常见问题

### 缩略图生成慢
- 首次访问时生成缩略图需要下载原图，可能较慢
- 之后直接从本地缓存读取

### 照片加载慢
- 百度网盘链接本身限速
- 高清大图可能需要几秒加载

### 链接失效
- 百度网盘直链约 8 小时有效
- 页面会自动重新获取

### 视频无法播放
- iPhone 拍摄的 HEVC/H.265 视频在某些浏览器不支持
- 建议用 Chrome 或 Safari

### 授权过期
```bash
bypy refreshtoken
```

## API 接口

- `GET /` - 相册首页
- `GET /api/files` - 获取文件列表（按日期分组）
- `GET /api/refresh` - 刷新文件索引
- `GET /thumb/<filename>` - 获取缩略图
- `GET /view/<filename>` - 查看原图/视频（302 重定向）
- `GET /api/url/<filename>` - 获取百度网盘直链

## 项目结构

```
babysit/
├── pyproject.toml          # 包配置
├── README.md               # 文档
├── babysit/                # 主包
│   ├── __init__.py
│   ├── app.py              # Flask 应用（含缩略图生成）
│   ├── config.py           # 配置
│   └── templates/
│       └── index.html      # 相册页面
```

## License

MIT
