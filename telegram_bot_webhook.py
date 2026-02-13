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
import cloudinary
import cloudinary.uploader
cloudinary.config( 
  secure = True
)
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


async def download_channel_avatar(chat_id: int, destination: str) -> bool:
    """Скачать аватарку канала"""
    try:
        # Получаем информацию о чате
        chat = await bot.get_chat(chat_id)
        if chat.photo:
            # Скачиваем большое фото (photo.big_file_id)
            await bot.download(chat.photo.big_file_id, destination)
            return True
    except Exception as e:
        print(f"Ошибка скачивания аватарки канала: {e}")
    return False


async def update_channel_info(name: str, avatar_url: str = ""):
    """Обновить информацию о канале через Flask API"""
    async with aiohttp.ClientSession() as session:
        data = {
            'name': name,
            'avatar_url': avatar_url or ''
        }
        try:
            async with session.post(f"{API_BASE_URL}/channel-info", json=data) as resp:
                if resp.status == 200:
                    print(f"✅ Информация о канале обновлена: {name}")
                    return True
        except Exception as e:
            print(f"Ошибка обновления channel-info: {e}")
        return False


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
    if message.chat.username and f"@{message.chat.username}" != CHANNEL_USERNAME:
        return

    media_type = None
    file_id = None

    # Определяем тип медиа
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        media_type = "video"
    elif message.animation:
        file_id = message.animation.file_id
        media_type = "video"

    if file_id:
            # 1. Получаем путь файла в Telegram
            file = await bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

            try:
                # 2. Загружаем в Cloudinary
                # Добавим resource_type="auto", чтобы корректно грузились и фото, и видео (GIF)
                upload_result = cloudinary.uploader.upload(
                    file_url, 
                    folder="telegram_posts",
                    resource_type="auto" 
                )
                
                # 3. Достаем прямую безопасную ссылку
                cloudinary_url = upload_result.get("secure_url")
                
                if not cloudinary_url:
                    print("❌ Не удалось получить URL от Cloudinary")
                    return

                print(f"🔗 Ссылка Cloudinary: {cloudinary_url}")

                # 4. Отправляем ССЫЛКУ в твой Flask API
                success = await send_to_api(
                    telegram_id=message.message_id,
                    media_type=media_type,
                    media_path=cloudinary_url, # ВАЖНО: Flask должен записать это в БД «как есть»
                    caption=message.caption
                )
                
                if success:
                    print(f"✅ Пост {message.message_id} успешно сохранен в БД через API")

            except Exception as e:
                print(f"❌ Ошибка Cloudinary или API: {e}")
            
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