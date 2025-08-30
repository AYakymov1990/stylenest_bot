# app/main.py
from fastapi import FastAPI

app = FastAPI()

# ---- ВАЖНО: подключаем платежные маршруты ----
from app.web.payments import router as payments_router
app.include_router(payments_router)

# (если делаешь админку — её тоже можно подключить)
# from app.admin.views import router as admin_router
# app.include_router(admin_router)

# healthcheck по желанию
@app.get("/health")
def health():
    return {"ok": True}
