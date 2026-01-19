[file name]: utils.py
[file content begin]
import pytz
from datetime import datetime, timedelta

def moscow_time():
    try: return datetime.now(pytz.timezone('Europe/Moscow'))
    except: return datetime.now()

def fmt_num(n): return f"{n:,}".replace(",", " ")

def progress_bar(val, total, length=20):
    filled = int((val/total*length)) if total else 0
    filled = max(0, min(filled, length))
    return "█"*filled + "░"*(length-filled)

def time_ago(ts):
    if not ts: return "никогда"
    diff = moscow_time() - ts
    if diff.days > 365: y=diff.days//365; return f"{y} год{'' if y==1 else 'а' if 2<=y<=4 else 'ов'} назад"
    if diff.days > 30: m=diff.days//30; return f"{m} месяц{'' if m==1 else 'а' if 2<=m<=4 else 'ев'} назад"
    if diff.days > 0: return f"{diff.days} день{'' if diff.days==1 else 'я' if 2<=diff.days<=4 else 'ей'} назад"
    if diff.seconds > 3600: h=diff.seconds//3600; return f"{h} час{'' if h==1 else 'а' if 2<=h<=4 else 'ов'} назад"
    if diff.seconds > 60: m=diff.seconds//60; return f"{m} минут{'' if m==1 else 'ы' if 2<=m<=4 else ''} назад"
    return "только что"

def median(data):
    if not data: return 0.0
    s=sorted(data); n=len(s)
    if n%2==1: return float(s[n//2])
    return (s[n//2-1]+s[n//2])/2

def percentile(data, p):
    if not data: return 0.0
    s=sorted(data); n=len(s); k=(n-1)*p/100
    f=int(k); c=k-f
    if f+1<n: return s[f]+c*(s[f+1]-s[f])
    return s[f]

def hourly_chart(hours, compact=False):
    if not hours or len(hours)!=24: return "⏰ Нет данных"
    if compact:
        lines=["<b>Активность (компактно):</b>"]
        for i in range(0,24,4):
            total=sum(hours[i:i+4]); mx=max([sum(hours[j:j+4]) for j in range(0,24,4)]) or 1
            bar_len=int((total/mx)*20); bar="█"*bar_len + "░"*(20-bar_len)
            lines.append(f"{i:02d}:00-{i+3:02d}:00: {bar} {total}")
        return "\n".join(lines)
    else:
        lines=["<b>Активность:</b>"]; mx=max(hours)
        if mx==0: return "⏰ Нет активности"
        for h in range(24):
            val=hours[h]; bar_len=int((val/mx)*15); bar="█"*bar_len + "░"*(15-bar_len)
            emoji="🌙" if 0<=h<6 else "🌅" if 6<=h<12 else "☀️" if 12<=h<18 else "🌆"
            lines.append(f"{emoji} {h:02d}:00: {bar} {val}")
        return "\n".join(lines)

def hour_emoji(h):
    if 0<=h<6: return "🌙"
    if 6<=h<12: return "🌅"
    if 12<=h<18: return "☀️"
    return "🌆"

def random_id(length=8):
    import string, secrets
    return ''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(length))

# Алиасы для обратной совместимости
get_moscow_time = moscow_time
format_number = fmt_num
create_progress_bar = progress_bar
format_time_ago = time_ago
calculate_median = median
calculate_percentile = percentile
generate_hourly_chart = hourly_chart
get_hour_emoji = hour_emoji
generate_random_id = random_id
[file content end]
