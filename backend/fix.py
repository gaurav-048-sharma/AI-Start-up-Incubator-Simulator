import re
with open(r'..\backend\app\api\routes\analytics.py', 'r', encoding='utf-8') as f:
    text = f.read()

if 'get_current_user' not in text:
    text = text.replace('from fastapi import APIRouter', 'from fastapi import APIRouter, Depends\nfrom app.middleware.security import get_current_user')

text = text.replace('async def get_usage_summary(user_id: str = "demo-user", days: int = 30):', 'async def get_usage_summary(days: int = 30, user: dict = Depends(get_current_user)):\n    user_id = user["id"]')

text = text.replace('async def get_credits(user_id: str = "demo-user"):', 'async def get_credits(user: dict = Depends(get_current_user)):\n    user_id = user["id"]')

text = text.replace('async def check_credits(event_type: str, user_id: str = "demo-user"):', 'async def check_credits(event_type: str, user: dict = Depends(get_current_user)):\n    user_id = user["id"]')

with open(r'..\backend\app\api\routes\analytics.py', 'w', encoding='utf-8') as f:
    f.write(text)

with open(r'..\backend\app\api\routes\notifications.py', 'r', encoding='utf-8') as f:
    text2 = f.read()
if 'get_current_user' not in text2:
    text2 = text2.replace('from fastapi import APIRouter', 'from fastapi import APIRouter, Depends\nfrom app.middleware.security import get_current_user')
text2 = re.sub(r'user_id: str = "demo-user"', 'user: dict = Depends(get_current_user)', text2)
text2 = re.sub(r'async def ([a-zA-Z_]+)\(.*?\):\n\s+"""', lambda m: m.group(0) + '\n    user_id = user["id"]', text2)
with open(r'..\backend\app\api\routes\notifications.py', 'w', encoding='utf-8') as f:
    f.write(text2)

with open(r'..\backend\app\api\routes\settings.py', 'r', encoding='utf-8') as f:
    text3 = f.read()
if 'get_current_user' not in text3:
    text3 = text3.replace('from fastapi import APIRouter', 'from fastapi import APIRouter, Depends\nfrom app.middleware.security import get_current_user')
text3 = re.sub(r'user_id: str = "demo-user"', 'user: dict = Depends(get_current_user)', text3)
text3 = re.sub(r'async def ([a-zA-Z_]+)\(.*?\):\n\s+"""', lambda m: m.group(0) + '\n    user_id = user["id"]', text3)
with open(r'..\backend\app\api\routes\settings.py', 'w', encoding='utf-8') as f:
    f.write(text3)
