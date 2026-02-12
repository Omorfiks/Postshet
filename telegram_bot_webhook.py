import asyncio
import aiohttp
import aiofiles
import os
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
load_dotenv()

# Конфигурация
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "8520214086:AAGCxdvMzMAGfBdqXH9K5HhQCp-kVDM4UmA")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@postshitpostshit")
_PORT = int(os.environ.get("PORT", 80))
API_BASE_URL = (os.environ.get("API_BASE_URL") or f"http://localhost:{_PORT}/api").rstrip("/")
LOGIN_TOKEN_SECRET = os.environ.get("LOGIN_TOKEN_SECRET", "")
# Важно: папка uploads должна быть доступна Flask-серверу
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads") 

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def download_media(file_id, destination):
    """Скачивает файл напрямую через bot.download"""
    try:
        await bot.download(file=file_id, destination=destination)
        return True
    except Exception as e:
        print(f"Ошибка скачивания: {e}")
        return False

async def send_to_api(telegram_id, media_type, media_path, caption=""):
    """Отправляет данные на Flask API"""
    async with aiohttp.ClientSession() as session:
        data = {
            'telegram_id': telegram_id,
            'media_type': media_type,
            'media_path': media_path,
            'caption': caption or ''
        }
        try:
            async with session.post(f"{API_BASE_URL}/posts", json=data) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"Ошибка связи с API: {e}")
            return False


async def create_login_token(telegram_id: int, first_name: str = "", last_name: str = "", username: str = "") -> str | None:
    """Запросить у Flask одноразовый токен для входа на сайт. Возвращает login_url или None."""
    if not LOGIN_TOKEN_SECRET:
        return None
    payload = {"secret": LOGIN_TOKEN_SECRET, "telegram_id": telegram_id}
    if first_name is not None:
        payload["first_name"] = first_name
    if last_name is not None:
        payload["last_name"] = last_name
    if username is not None:
        payload["username"] = username.lstrip("@")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{API_BASE_URL}/create-login-token",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if data.get("ok") and data.get("login_url"):
                    return data["login_url"]
        except Exception as e:
            print(f"Ошибка create-login-token: {e}")
    return None


@dp.message(F.text.startswith("/start"))
async def handle_start(message: Message):
    """Вход на сайт: /start login — бот присылает ссылку для входа."""
    payload = (message.text or "").strip().split(maxsplit=1)
    if len(payload) < 2 or payload[1].lower() != "login":
        return
    user = message.from_user
    if not user:
        return
    login_url = await create_login_token(
        user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
    )
    if not login_url:
        await message.answer("Сервис входа временно недоступен. Попробуйте позже.")
        return
    text = (
        "Чтобы войти на сайте в обычном браузере (Chrome, Safari и т.д.), "
        "откройте ссылку ниже в браузере:\n\n"
        "📲 Длинное нажатие по ссылке → «Открыть в браузере»\n"
        "или скопируйте ссылку и вставьте в адресную строку браузера.\n\n"
        f"{login_url}"
    )
    await message.answer(text)


# Используем router для постов канала (channel_post)
@dp.channel_post()
async def handle_channel_post(message: Message):
    # Проверка юзернейма (опционально, если бот только в одном канале)
    if message.chat.username and f"@{message.chat.username}" != CHANNEL_USERNAME:
        return

    media_type = None
    file_id = None
    ext = "jpg"

    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
        ext = "jpg"
    elif message.video:
        file_id = message.video.file_id
        media_type = "video"
        ext = "mp4"
    elif message.animation:
        file_id = message.animation.file_id
        media_type = "video"
        ext = "mp4" # Сейвим гифки как видео

    if file_id:
        filename = f"{message.message_id}_{datetime.now().strftime('%H%M%S')}.{ext}"
        full_path = os.path.join(UPLOAD_FOLDER, filename)
        
        if await download_media(file_id, full_path):
            # Передаем относительный путь для сайта
            relative_path = filename 
            await send_to_api(message.message_id, media_type, relative_path, message.caption)
            print(f"✅ Пост {message.message_id} отправлен на сайт.")

async def on_startup(bot: Bot):
    # Устанавливаем Webhook при запуске
    webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL')}/webhook"
    await bot.set_webhook(webhook_url)
    print(f"✅ Webhook установлен на: {webhook_url}")

def main():
    # Настройки адреса
    # На Render переменная PORT подставляется автоматически
    WEB_SERVER_HOST = "0.0.0.0"
    WEB_SERVER_PORT = int(os.environ.get("PORT", 8080))
    
    app = web.Application()

    # Привязываем aiogram к пути /webhook
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path="/webhook")

    # Регистрируем функцию запуска
    setup_application(app, dp, bot=bot)
    app.on_startup.append(lambda _: on_startup(bot))

    # Запускаем сервер
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)

if __name__ == "__main__":
    main()