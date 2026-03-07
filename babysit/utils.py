"""工具函数模块"""
from datetime import datetime, date


def calculate_age(birthday):
    """计算月龄"""
    if not birthday:
        return None
    birth = datetime.strptime(birthday, "%Y-%m-%d").date() if isinstance(birthday, str) else birthday
    today = date.today()
    months = (today.year - birth.year) * 12 + (today.month - birth.month)
    if today.day < birth.day:
        months -= 1
    return max(0, months)
