import pytz
from datetime import datetime, timedelta

def moscow_time():
    try: return datetime.now(pytz.timezone('Europe/Moscow'))
    except: return datetime.now()

def fmt_num(n): return f"{n:,}".replace(",", " ")

def fmt_percent(val, total): return f"{(val/total*100):.1f}%" if total else "0.0%"

def progress_bar(val, total, length=20):
    filled = int((val/total*length)) if total else 0
    filled = max(0, min(filled, length))
    return "█"*filled + "░"*(length-filled)

def truncate(txt, max_len=100, suffix="..."):
    return txt[:max_len-len(suffix)] + suffix if len(txt)>max_len else txt

def time_ago(ts):
    if not ts: return "никогда"
    diff = moscow_time() - ts
    if diff.days > 365: y=diff.days//365; return f"{y} год{'' if y==1 else 'а' if 2<=y<=4 else 'ов'} назад"
    if diff.days > 30: m=diff.days//30; return f"{m} месяц{'' if m==1 else 'а' if 2<=m<=4 else 'ев'} назад"
    if diff.days > 0: return f"{diff.days} день{'' if diff.days==1 else 'я' if 2<=diff.days<=4 else 'ей'} назад"
    if diff.seconds > 3600: h=diff.seconds//3600; return f"{h} час{'' if h==1 else 'а' if 2<=h<=4 else 'ов'} назад"
    if diff.seconds > 60: m=diff.seconds//60; return f"{m} минут{'' if m==1 else 'ы' if 2<=m<=4 else ''} назад"
    return "только что"

def fmt_duration(sec):
    if sec<60: return f"{sec} сек"
    if sec<3600: return f"{sec//60} мин"
    if sec<86400: return f"{sec//3600} ч {(sec%3600)//60} мин"
    return f"{sec//86400} д {(sec%86400)//3600} ч"

def fmt_date_range(days):
    if days==1: return "сегодня"
    if days==7: return "за неделю"
    if days==30: return "за месяц"
    if days==365: return "за год"
    return f"за {days} дней"

def avg(data): return sum(data)/len(data) if data else 0.0

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

def chart(data, width=50):
    if not data: return "📊 Нет данных"
    mx=max(data.values())
    if mx==0: return "📊 Все нули"
    lines=[]
    for label,val in data.items():
        bar_len=int((val/mx)*width); bar="█"*bar_len + "░"*(width-bar_len)
        lines.append(f"{label}: {bar} {val}")
    return "\n".join(lines)

def hourly_chart(hours, compact=False):
    if not hours or len(hours)!=24: return "⏰ Нет данных"
    if compact:
        lines=["⏰ *Активность (компактно):*"]
        for i in range(0,24,4):
            total=sum(hours[i:i+4]); mx=max([sum(hours[j:j+4]) for j in range(0,24,4)]) or 1
            bar_len=int((total/mx)*20); bar="█"*bar_len + "░"*(20-bar_len)
            lines.append(f"{i:02d}:00-{i+3:02d}:00: {bar} {total}")
        return "\n".join(lines)
    else:
        lines=["⏰ *Активность:*"]; mx=max(hours)
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

def day_emoji(d): return ["😴","😞","😐","🙂","😊","🎉","🎊"][d.weekday()]

def stats_summary(stats):
    lines=[]
    if 'total' in stats: lines.append(f"📊 Всего: {fmt_num(stats['total'])}")
    if 'average' in stats: lines.append(f"📈 Среднее: {stats['average']:.1f}")
    if 'median' in stats: lines.append(f"⚖️ Медиана: {stats['median']:.1f}")
    if 'max' in stats: lines.append(f"🏆 Максимум: {stats['max']}")
    if 'min' in stats and stats['min']>0: lines.append(f"📉 Минимум: {stats['min']}")
    return "\n".join(lines)

def safe_div(num, den, default=0.0): return num/den if den else default

def random_id(length=8):
    import string, secrets
    return ''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(length))

def parse_time_range(tr):
    now=moscow_time()
    if tr=="today": start=now.replace(hour=0,minute=0,second=0,microsecond=0); end=now
    elif tr=="week": start=now-timedelta(days=7); end=now
    elif tr=="month": start=now-timedelta(days=30); end=now
    elif tr=="year": start=now-timedelta(days=365); end=now
    else: start=datetime(2020,1,1); end=now
    return start, end

def humanize_num(n):
    if n<1000: return str(n)
    if n<1000000: return f"{n/1000:.1f}K".replace(".0","")
    if n<1000000000: return f"{n/1000000:.1f}M".replace(".0","")
    return f"{n/1000000000:.1f}B".replace(".0","")

get_moscow_time = moscow_time
format_number = fmt_num
format_percentage = fmt_percent
create_progress_bar = progress_bar
truncate_text = truncate
format_time_ago = time_ago
format_duration = fmt_duration
format_date_range = fmt_date_range
calculate_average = avg
calculate_median = median
calculate_percentile = percentile
generate_chart = chart
generate_hourly_chart = hourly_chart
get_hour_emoji = hour_emoji
get_day_of_week_emoji = day_emoji
format_statistics_summary = stats_summary
safe_division = safe_div
generate_random_id = random_id
parse_time_range = parse_time_range
humanize_number = humanize_num
