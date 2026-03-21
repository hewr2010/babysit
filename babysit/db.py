"""数据库模块"""
import sqlite3
from flask import g
from .config import DB_PATH


def _configure_connection(db):
    """配置数据库连接（启用 WAL 模式等）"""
    # 启用 WAL 模式，提高并发性能
    db.execute("PRAGMA journal_mode=WAL")
    # 设置同步模式为 NORMAL，平衡性能和安全性
    db.execute("PRAGMA synchronous=NORMAL")
    # 设置忙等待超时（毫秒），避免 "database is locked" 错误
    db.execute("PRAGMA busy_timeout=5000")


def get_db():
    """获取 Flask 应用上下文中的数据库连接"""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        _configure_connection(g.db)
    return g.db


def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db:
        db.close()


def init_db():
    """初始化数据库表"""
    db = sqlite3.connect(DB_PATH)
    _configure_connection(db)
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS baby (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            birthday DATE NOT NULL,
            gender TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            amount REAL,
            unit TEXT,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS growth (
            id INTEGER PRIMARY KEY,
            date DATE NOT NULL,
            metric_type TEXT NOT NULL,
            value REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 媒体文件表 - 用于存储已预处理的媒体文件信息
    db.execute('''
        CREATE TABLE IF NOT EXISTS media_files (
            id INTEGER PRIMARY KEY,
            filename TEXT UNIQUE NOT NULL,
            file_type TEXT NOT NULL,  -- 'photo' 或 'video'
            file_size INTEGER,
            md5 TEXT,
            date TEXT NOT NULL,  -- 拍摄日期 YYYY-MM-DD
            time TEXT,  -- 拍摄时间 HH:MM
            baidu_date TEXT,  -- 百度网盘上的日期
            processed BOOLEAN DEFAULT 0,  -- 是否已完成预处理
            processed_at TIMESTAMP,  -- 预处理完成时间
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            -- 为常用查询创建索引
            UNIQUE(filename)
        )
    ''')
    
    # 创建索引以优化查询性能
    db.execute('''
        CREATE INDEX IF NOT EXISTS idx_media_date ON media_files(date DESC)
    ''')
    db.execute('''
        CREATE INDEX IF NOT EXISTS idx_media_processed ON media_files(processed, date DESC)
    ''')
    
    # 重要时刻表 - 标记照片的重要时刻
    db.execute('''
        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY,
            media_filename TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (media_filename) REFERENCES media_files(filename),
            UNIQUE(media_filename, title)
        )
    ''')
    db.execute('''
        CREATE INDEX IF NOT EXISTS idx_milestones_filename ON milestones(media_filename)
    ''')
    db.execute('''
        CREATE INDEX IF NOT EXISTS idx_milestones_created ON milestones(created_at DESC)
    ''')
    
    # 初始化默认宝宝信息（青青）
    cursor = db.execute("SELECT COUNT(*) FROM baby")
    if cursor.fetchone()[0] == 0:
        db.execute(
            "INSERT INTO baby (name, birthday, gender) VALUES (?, ?, ?)",
            ("青青", "2026-02-12", "女")
        )
        print("✓ 已初始化宝宝信息: 青青, 女, 2026-02-12")
    
    db.commit()
    db.close()


# ===== 宝宝信息 =====
def get_baby():
    """获取宝宝信息"""
    db = get_db()
    row = db.execute("SELECT * FROM baby ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def add_baby(data):
    """添加宝宝"""
    db = get_db()
    db.execute("DELETE FROM baby")  # 只允许一个宝宝
    db.execute(
        "INSERT INTO baby (name, birthday, gender) VALUES (?, ?, ?)",
        (data['name'], data['birthday'], data.get('gender'))
    )
    db.commit()


# ===== 成长记录 =====
def get_growth_records():
    """获取所有成长记录 (按指标类型分开)"""
    db = get_db()
    rows = db.execute("SELECT * FROM growth ORDER BY date DESC, metric_type").fetchall()
    return [dict(r) for r in rows]


def add_growth(data):
    """添加成长记录 (支持单个或多个指标)"""
    db = get_db()
    date = data['date']
    
    # 分别添加每个指标
    if data.get('height'):
        db.execute(
            "INSERT INTO growth (date, metric_type, value) VALUES (?, ?, ?)",
            (date, 'height', float(data['height']))
        )
    
    if data.get('weight'):
        db.execute(
            "INSERT INTO growth (date, metric_type, value) VALUES (?, ?, ?)",
            (date, 'weight', float(data['weight']))
        )
    
    db.commit()


def delete_growth(id):
    """删除成长记录"""
    db = get_db()
    db.execute("DELETE FROM growth WHERE id = ?", (id,))
    db.commit()


# ===== 媒体文件（供 refresh_media 进程使用）=====
def get_standalone_db():
    """获取独立的数据库连接（用于非 Flask 上下文，如 refresh_media 进程）"""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    _configure_connection(db)
    return db


def update_media_file(db, file_info):
    """
    更新或插入媒体文件记录
    参数 db 是已建立的数据库连接
    """
    db.execute('''
        INSERT INTO media_files 
        (filename, file_type, file_size, md5, date, time, baidu_date, processed, processed_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(filename) DO UPDATE SET
            file_type = excluded.file_type,
            file_size = excluded.file_size,
            md5 = excluded.md5,
            date = excluded.date,
            time = excluded.time,
            baidu_date = excluded.baidu_date,
            processed = excluded.processed,
            processed_at = excluded.processed_at,
            updated_at = CURRENT_TIMESTAMP
    ''', (
        file_info['name'],
        file_info['type'],
        file_info.get('size'),
        file_info.get('md5'),
        file_info['date'],
        file_info.get('time', ''),
        file_info.get('baidu_date', ''),
        file_info.get('processed', False),
        file_info.get('processed_at')
    ))


def delete_media_file(db, filename):
    """删除媒体文件记录"""
    db.execute("DELETE FROM media_files WHERE filename = ?", (filename,))


def _get_processed_media_rows(db):
    """从数据库获取已处理媒体文件的原始行数据"""
    return db.execute('''
        SELECT filename, file_type, file_size, md5, date, time, baidu_date, processed_at
        FROM media_files
        WHERE processed = 1
        ORDER BY date DESC, time DESC
    ''').fetchall()


def _rows_to_grouped_dict(rows):
    """将数据库行转换为按日期分组的字典"""
    result = {}
    for row in rows:
        date = row['date']
        if date not in result:
            result[date] = []
        result[date].append({
            'name': row['filename'],
            'type': row['file_type'],
            'size': row['file_size'],
            'md5': row['md5'],
            'date': row['date'],
            'time': row['time'] or '',
            'baidu_date': row['baidu_date'],
            'processed_at': row['processed_at']
        })
    return result


def get_all_processed_media():
    """获取所有已预处理的媒体文件（按日期分组）- 供 Flask 使用"""
    db = get_db()
    rows = _get_processed_media_rows(db)
    return _rows_to_grouped_dict(rows)


def get_standalone_processed_media():
    """获取所有已预处理的媒体文件（按日期分组）- 供独立进程使用"""
    db = get_standalone_db()
    try:
        rows = _get_processed_media_rows(db)
        return _rows_to_grouped_dict(rows)
    finally:
        db.close()


def _filter_by_month(grouped_media, year, month):
    """从已分组的数据中筛选指定月份"""
    prefix = f"{year}-{month:02d}"
    result = {}
    for date, files in grouped_media.items():
        if date.startswith(prefix):
            result[date] = files
    return result


def get_processed_media_by_month(year, month):
    """获取指定月份的已预处理媒体文件 - 供 Flask 使用"""
    all_media = get_all_processed_media()
    return _filter_by_month(all_media, year, month)


def get_standalone_processed_media_by_month(year, month):
    """获取指定月份的已预处理媒体文件 - 供独立进程使用"""
    all_media = get_standalone_processed_media()
    return _filter_by_month(all_media, year, month)


def get_media_filenames():
    """获取所有媒体文件名（用于清理不存在的记录）"""
    db = get_db()
    rows = db.execute("SELECT filename FROM media_files").fetchall()
    return {row['filename'] for row in rows}


# ===== 重要时刻 =====
def get_all_milestones():
    """获取所有重要时刻，包含媒体文件信息"""
    db = get_db()
    rows = db.execute('''
        SELECT m.id, m.media_filename, m.title, m.description, m.created_at,
               mf.date, mf.time, mf.file_type
        FROM milestones m
        JOIN media_files mf ON m.media_filename = mf.filename
        ORDER BY mf.date DESC, mf.time DESC
    ''').fetchall()
    return [dict(r) for r in rows]


def get_milestones_by_filename(filename):
    """获取某张照片关联的所有重要时刻"""
    db = get_db()
    rows = db.execute('''
        SELECT id, media_filename, title, description, created_at
        FROM milestones
        WHERE media_filename = ?
        ORDER BY created_at DESC
    ''', (filename,)).fetchall()
    return [dict(r) for r in rows]


def add_milestone(data):
    """添加重要时刻
    data: {media_filename, title, description}
    """
    db = get_db()
    db.execute('''
        INSERT INTO milestones (media_filename, title, description)
        VALUES (?, ?, ?)
        ON CONFLICT(media_filename, title) DO UPDATE SET
            description = excluded.description,
            created_at = CURRENT_TIMESTAMP
    ''', (data['media_filename'], data['title'], data.get('description')))
    db.commit()


def delete_milestone(id):
    """删除重要时刻"""
    db = get_db()
    db.execute('DELETE FROM milestones WHERE id = ?', (id,))
    db.commit()


def get_milestone(id):
    """获取单个重要时刻详情"""
    db = get_db()
    row = db.execute('''
        SELECT m.id, m.media_filename, m.title, m.description, m.created_at,
               mf.date, mf.time, mf.file_type
        FROM milestones m
        JOIN media_files mf ON m.media_filename = mf.filename
        WHERE m.id = ?
    ''', (id,)).fetchone()
    return dict(row) if row else None
