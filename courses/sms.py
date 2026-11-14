"""
ارسال پیامک با کاوه‌نگار (kavenegar.com)
برای فعال شدن باید توی config/settings.py این دو مقدار رو پر کنی:
    KAVENEGAR_API_KEY = "..."
    ADMIN_PHONE_NUMBER = "09xxxxxxxxx"
تا وقتی پر نشدن، ارسال پیامک به‌آرومی رد می‌شه (سایت خطا نمی‌ده).
"""
import json
import urllib.request
import urllib.parse
from django.conf import settings


def send_admin_sms(message: str) -> bool:
    api_key = getattr(settings, "KAVENEGAR_API_KEY", "")
    receptor = getattr(settings, "ADMIN_PHONE_NUMBER", "")

    if not api_key or not receptor:
        # هنوز تنظیم نشده - چیزی ارسال نمی‌شه ولی سایت هم خطا نمی‌ده
        return False

    url = f"https://api.kavenegar.com/v1/{api_key}/sms/send.json"
    data = urllib.parse.urlencode({
        "receptor": receptor,
        "message": message,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=8) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("return", {}).get("status") == 200
    except Exception:
        # مشکل شبکه یا کلید اشتباه - سایت رو خراب نمی‌کنیم
        return False
