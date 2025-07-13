from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+ 内置模块


def get_day_of_week():
    # 直接获取当前东九区时间（Asia/Tokyo）
    now_time = datetime.now(ZoneInfo("Asia/Tokyo"))

    # 提取星期几（中文）、小时、分钟
    day = now_time.isoweekday()  # isoweekday() 返回 1（周一）~7（周日）
    hour = now_time.hour  # 小时（0-23）

    if hour < 6:
        day -= 1

    return day

def calculate_the_teams():
    day = get_day_of_week()
    if day == 1 or day == 2:
        return "1_2"
    if day == 3 or day == 4:
        return "3_4"
    if day == 5 or day == 6:
        return "5_6"
    if day == 7 or day == 8:
        return "7"