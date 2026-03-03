"""数据库模块"""
import sqlite3
from flask import g
from .config import DB_PATH

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()

def init_db():
    """初始化数据库表"""
    db = sqlite3.connect(DB_PATH)
    
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

# 查询函数
def get_baby():
    """获取宝宝信息"""
    db = get_db()
    row = db.execute("SELECT * FROM baby ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None

def get_records_by_month(year, month):
    """获取某月所有记录"""
    db = get_db()
    start = f"{year}-{month:02d}-01"
    # 计算下月第一天
    if month == 12:
        end = f"{year+1}-01-01"
    else:
        end = f"{year}-{month+1:02d}-01"
    
    rows = db.execute(
        "SELECT * FROM records WHERE date(start_time) >= ? AND date(start_time) < ? ORDER BY start_time",
        (start, end)
    ).fetchall()
    return [dict(r) for r in rows]

def add_baby(data):
    """添加宝宝"""
    db = get_db()
    db.execute("DELETE FROM baby")  # 只允许一个宝宝
    db.execute(
        "INSERT INTO baby (name, birthday, gender) VALUES (?, ?, ?)",
        (data['name'], data['birthday'], data.get('gender'))
    )
    db.commit()

def add_record(data):
    """添加记录"""
    db = get_db()
    db.execute(
        "INSERT INTO records (type, start_time, end_time, amount, unit, note) VALUES (?, ?, ?, ?, ?, ?)",
        (data['type'], data.get('start_time'), data.get('end_time'),
         data.get('amount'), data.get('unit'), data.get('note'))
    )
    db.commit()

def delete_record(id):
    """删除记录"""
    db = get_db()
    db.execute("DELETE FROM records WHERE id = ?", (id,))
    db.commit()

# ===== 生长记录 =====
def get_growth_records():
    """获取所有生长记录 (按指标类型分开)"""
    db = get_db()
    rows = db.execute("SELECT * FROM growth ORDER BY date DESC, metric_type").fetchall()
    return [dict(r) for r in rows]

def add_growth(data):
    """添加生长记录 (支持单个或多个指标)"""
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
    """删除生长记录"""
    db = get_db()
    db.execute("DELETE FROM growth WHERE id = ?", (id,))
    db.commit()

def get_yesterday_summary():
    """获取昨日总结"""
    from datetime import datetime, timedelta
    db = get_db()
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 喂奶次数和总量
    feeding_row = db.execute(
        "SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total FROM records WHERE type='feeding' AND date(start_time) = ?",
        (yesterday,)
    ).fetchone()
    feeding_count = feeding_row['count']
    feeding_total = feeding_row['total']
    
    # 大便次数
    poop_row = db.execute(
        "SELECT COUNT(*) as count FROM records WHERE type='poop' AND date(start_time) = ?",
        (yesterday,)
    ).fetchone()
    poop_count = poop_row['count']
    
    # 小便次数
    pee_row = db.execute(
        "SELECT COUNT(*) as count FROM records WHERE type='pee' AND date(start_time) = ?",
        (yesterday,)
    ).fetchone()
    pee_count = pee_row['count']
    
    return {
        'feeding_count': feeding_count or '-',
        'feeding_total': feeding_total or 0,
        'poop_count': poop_count or '-',
        'pee_count': pee_count or '-'
    }
