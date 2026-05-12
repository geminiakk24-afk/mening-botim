import asyncio
import os
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- SOZLAMALAR ---
TOKEN = os.getenv("BOT_TOKEN", "8185111678:AAG2fycO550HyYxB2AV2VS1srAzYA_J8X4Y")
ADMIN_ID = 7751791288
CHANNELS = []
COOKIE_FILE = "instagram.com_cookies.txt"

# --- PROKSILAR ---
PROXIES = [
    "http://gofactvd:hywvsnkhr45b@31.59.20.176:6754",
    "http://gofactvd:hywvsnkhr45b@31.56.127.193:7684",
    "http://gofactvd:hywvsnkhr45b@45.38.107.97:6014",
    "http://gofactvd:hywvsnkhr45b@107.172.163.27:6543",
    "http://gofactvd:hywvsnkhr45b@198.23.243.226:6361",
    "http://gofactvd:hywvsnkhr45b@216.10.27.159:6837",
    "http://gofactvd:hywvsnkhr45b@142.111.67.146:5611",
    "http://gofactvd:hywvsnkhr45b@191.96.254.138:6185",
    "http://gofactvd:hywvsnkhr45b@31.58.9.4:6077",
    "http://gofactvd:hywvsnkhr45b@23.229.19.94:8689",
]

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- BAZA ---
async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
        await db.commit()

async def add_user(user_id: int):
    async with aiosqlite.connect("users.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()

# --- OBUNANI TEKSHIRISH ---
async def check_sub(user_id: int) -> bool:
    if not CHANNELS:
        return True
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ("left", "kicked", "banned"):
                return False
        except Exception as e:
            logger.warning(f"Kanal tekshirishda xato ({channel}): {e}")
            return False
    return True

# --- VIDEO YUKLASH ---
def download_video(url: str) -> str:
    is_instagram = "instagram.com" in url

    # Avval proksisiz sinab ko'ramiz
    ydl_opts = {
        "format": "best[filesize<50M]/best",
        "outtmpl": "video_%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
    }

    if is_instagram and os.path.exists(COOKIE_FILE):
        ydl_opts["cookiefile"] = COOKIE_FILE

    # Instagram uchun proksi bilan sinab ko'ramiz
    if is_instagram:
        for proxy in PROXIES:
            try:
                ydl_opts["proxy"] = proxy
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return ydl.prepare_filename(info)
            except Exception as e:
                logger.warning(f"Proksi {proxy} ishlamadi: {e}")
                continue
        raise Exception("Barcha proksilar ishlamadi")
    else:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

# --- /start ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await add_user(message.from_user.id)
    await message.answer(
        "👋 Salom! Video yuklovchi botga xush kelibsiz!\n\n"
        "📎 Videoni yuklash uchun link yuboring (YouTube, Instagram, TikTok va boshqalar)."
    )

# --- LINK KELGANDA ---
@dp.message(F.text.startswith("http"))
async def handle_link(message: types.Message):
    is_sub = await check_sub(message.from_user.id)

    if not is_sub:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Kanalga obuna bo'lish ➕", url=f"https://t.me/{CHANNELS[0][1:]}")],
            [InlineKeyboardButton(text="Tekshirish ✅", callback_data="check")]
        ])
        await message.answer(
            "⚠️ Botdan foydalanish uchun kanalimizga a'zo bo'ling!",
            reply_markup=keyboard
        )
        return

    status_msg = await message.answer("⏳ Video yuklanmoqda, biroz kuting...")

    try:
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(None, download_video, message.text)

        if not os.path.exists(file_path):
            await status_msg.edit_text("❌ Fayl topilmadi. Link to'g'ri ekanligini tekshiring.")
            return

        video_file = FSInputFile(file_path)
        await message.answer_video(
            video_file,
            caption="✅ Mana video!\n\n📌 @byamirovyukla_bot"
        )

    except Exception as e:
        logger.error(f"Video yuklashda xato: {e}")
        await status_msg.edit_text(
            "❌ Xatolik yuz berdi. Mumkin bo'lgan sabablar:\n"
            "• Link noto'g'ri yoki o'chirilgan\n"
            "• Video juda katta (50MB dan oshmasligi kerak)\n"
            "• Sayt qo'llab-quvvatlanmaydi"
        )

    finally:
        if "file_path" in locals() and os.path.exists(file_path):
            os.remove(file_path)
        try:
            await status_msg.delete()
        except Exception:
            pass

# --- TEKSHIRISH KNOPKASI ---
@dp.callback_query(F.data == "check")
async def check_callback(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Rahmat! Endi video linkini yuborishingiz mumkin.")
    else:
        await call.answer("❌ Siz hali a'zo bo'lmadingiz!", show_alert=True)

# --- MAIN ---
async def main():
    await init_db()
    logger.info("Bot ishga tushdi...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
