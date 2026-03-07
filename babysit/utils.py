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

def get_hour_slot(dt_str):
    """获取时段 (0-23)"""
    if not dt_str:
        return None
    if isinstance(dt_str, str):
        # 解析 ISO 格式时间
        if 'T' in dt_str:
            dt_str = dt_str.replace('T', ' ')
        if len(dt_str) >= 13:
            try:
                hour = int(dt_str[11:13])
                return hour
            except:
                pass
    return None

def get_month_days(year, month):
    """获取某月的天数"""
    import calendar
    return calendar.monthrange(year, month)[1]

def format_month_data(records, year, month):
    """格式化月度数据为热力图格式"""
    from datetime import datetime, timedelta
    days_in_month = get_month_days(year, month)
    
    # 初始化数据结构: {day: {hour: [types]}}
    data = {}
    for day in range(1, days_in_month + 1):
        data[day] = {}
    
    for r in records:
        start_time = r.get('start_time', '')
        end_time = r.get('end_time', '')
        record_type = r['type']
        
        if not start_time:
            continue
        
        try:
            # 解析开始时间
            if isinstance(start_time, str):
                if 'T' in start_time:
                    start_time = start_time.replace('T', ' ')
                start_dt = datetime.strptime(start_time[:19], '%Y-%m-%d %H:%M:%S')
            else:
                continue
            
            # 对于睡眠记录，如果有结束时间，填充所有小时
            if record_type == 'sleep' and end_time:
                if 'T' in end_time:
                    end_time = end_time.replace('T', ' ')
                end_dt = datetime.strptime(end_time[:19], '%Y-%m-%d %H:%M:%S')
                
                # 遍历所有小时
                current = start_dt
                while current <= end_dt:
                    day = current.day
                    hour = current.hour
                    
                    if day in data:
                        if hour not in data[day]:
                            data[day][hour] = []
                        
                        # 避免重复添加（同一条记录）
                        if not any(item.get('id') == r['id'] for item in data[day][hour]):
                            data[day][hour].append({
                                'id': r['id'],
                                'type': record_type,
                                'amount': r.get('amount'),
                                'unit': r.get('unit'),
                                'note': r.get('note'),
                                'start_time': r.get('start_time'),
                                'end_time': r.get('end_time')
                            })
                    
                    current += timedelta(hours=1)
            else:
                # 非睡眠记录或没有结束时间，只放在开始时间
                day = start_dt.day
                hour = start_dt.hour
                
                if day in data:
                    if hour not in data[day]:
                        data[day][hour] = []
                    
                    data[day][hour].append({
                        'id': r['id'],
                        'type': record_type,
                        'amount': r.get('amount'),
                        'unit': r.get('unit'),
                        'note': r.get('note'),
                        'start_time': r.get('start_time'),
                        'end_time': r.get('end_time')
                    })
        except Exception as e:
            print(f"Error processing record {r.get('id')}: {e}")
            continue
    
    return data
