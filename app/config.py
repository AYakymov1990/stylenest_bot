from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # БД: по умолчанию SQLite-файл в корне проекта
    DATABASE_URL: str = "sqlite:///./stylenest.db"

    # Telegram (для будущих шагов)
    BOT_TOKEN: str = "8443212310:AAExxy7I3joBTJz2v0bbyo0fZnjFz2XDrmw"
    ADMIN_IDS: str = ""   # "123,456" (позже пригодится)

    # Канал (для будущих шагов)
    CHANNEL_ID: int = -1003030284296

    # Webhook (нужно для прода)
    PUBLIC_BASE_URL: str = ""         # пример: "https://<user>.pythonanywhere.com"
    WEBHOOK_SECRET: str = "dev-secret"

    # WayForPay
    WFP_MERCHANT_ACCOUNT: str = "t_me_29475"
    WFP_MERCHANT_DOMAIN: str = "5a48d4465205.ngrok-free.app"
    WFP_MERCHANT_SECRET: str = "42127b907c979094f8b73214fb9df926e6c593c0"
    WFP_CURRENCY: str = "UAH"
    WFP_API_URL: str = "https://api.wayforpay.com/api"
    WFP_SERVICE_URL: str = "https://5a48d4465205.ngrok-free.app/wfp/callback"
    WFP_RETURN_URL: str = "https://t.me/stylenest_club_bot?start=thankyou"          # ← важно, чтобы поле существовало
    WFP_FORCE_TEST_AMOUNT: int = 0

    # прочее
    API_BASE_URL: str = "http://localhost:8080"
    CHANNEL_ID: int | None = None

    # Отображение цен в EUR
    TARIFF_1M_PRICE_EUR: int = 15
    TARIFF_2M_PRICE_EUR: int = 28
    TARIFF_3M_PRICE_EUR: int = 40

    # Суммы для инвойса (локальная валюта — для мок/реальной оплаты)
    LOCAL_CURRENCY: str = "UAH"
    TARIFF_1M_PRICE_LOCAL: int = 1
    TARIFF_2M_PRICE_LOCAL: int = 2
    TARIFF_3M_PRICE_LOCAL: int = 3

    # путь к фото для /start
    START_IMAGE_PATH: str = "app/assets/IMG_0022.PNG"
# опционально: file_id уже загруженного фото в TG (оставь пустым)
    START_PHOTO_FILE_ID: str = ""

    # Где хранится промо-фото для winback (файл положи рядом с другими ассетами)
    WINBACK_IMAGE_PATH: str = "app/assets/IMG_0796.PNG"

    # Этапы winback в днях (3, 7, 30)
    WINBACK_STAGES: tuple[int, ...] = (3, 7, 30)


settings = Settings()