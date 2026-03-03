import os
import sqlite3
import logging
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
FORUM_CHAT_ID = int(os.getenv("ADMIN_FORUM_CHAT_ID", "0"))

if not BOT_TOKEN or not ADMIN_ID or not FORUM_CHAT_ID:
    raise RuntimeError("BOT_TOKEN / ADMIN_ID / ADMIN_FORUM_CHAT_ID eksik.")

DB_PATH = "relay.db"

def db_init():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_topic_map (
            user_id INTEGER PRIMARY KEY,
            topic_id INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS topic_user_map (
            topic_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def db_get_topic(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT topic_id FROM user_topic_map WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def db_get_user(topic_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM topic_user_map WHERE topic_id = ?", (topic_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def db_set(user_id: int, topic_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO user_topic_map (user_id, topic_id) VALUES (?, ?)", (user_id, topic_id))
    cur.execute("INSERT OR REPLACE INTO topic_user_map (topic_id, user_id) VALUES (?, ?)", (topic_id, user_id))
    conn.commit()
    conn.close()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

WELCOME_TEXT = (
    "👋 Merhaba, size her türlü destek sağlayabilirim.\n\n"
    "📌 İsim Soyisim'den Tc NO, Telefon, Aile TC VE İKAMETGAH\n"
    "📌 Plakadan Şahıs , Numara, Adres, Araç Bilgileri.\n"
    "📌 Kişiden , Araç Bilgileri..\n"
    "📌 Kişiden Aynı İkamet Eden Hane Bilgileri.\n"
    "📌 Kişiden Aynı Sokak, Mahalle, Apartman Bilgileri.\n"
    "📌 Kişiden Detaylı Numara Bilgileri \n\n"
    "📌 Numaradan Detaylı Kişi Bilgiler \n\n"
    "📌 SeriNo - Skt Bilgileri \n\n"
    "📌 Trafik Ceza \n\n"
    "📌 Güncel Hane \n\n"
    "📌 Kişiden Tapu Bilgileri (81 il 102 milyon Veri ) \n\n"
    "📌 Ada Parselden Şahıs Bilgileri (56 il 98milyon Veri ) \n\n"
    "Detayları mesaj olarak yazmanız yeterlidir."
)

AUTO_REPLY_TEXT = (
    "✅ Mesajınızı aldım.\n"
    "En kısa sürede size dönüş yapılacak."
)

async def ensure_topic_for_user(user_id: int, user_name: str) -> int:
    topic_id = db_get_topic(user_id)
    if topic_id:
        return topic_id

    title = f"{user_name} ({user_id})"
    created = await bot.create_forum_topic(chat_id=FORUM_CHAT_ID, name=title)
    topic_id = created.message_thread_id
    db_set(user_id, topic_id)

    await bot.send_message(
        chat_id=FORUM_CHAT_ID,
        message_thread_id=topic_id,
        text=f"✅ Yeni kullanıcı: {user_name}\nUserID: {user_id}"
    )
    return topic_id

async def send_user_message_to_topic(message: Message):
    user_id = message.from_user.id
    user_name = (message.from_user.full_name or "Kullanıcı").strip()
    topic_id = await ensure_topic_for_user(user_id, user_name)

    await bot.copy_message(
        chat_id=FORUM_CHAT_ID,
        message_thread_id=topic_id,
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )

@dp.message(CommandStart(), F.from_user.id != ADMIN_ID)
async def start_handler(message: Message):
    await message.answer(WELCOME_TEXT)
    await send_user_message_to_topic(message)

@dp.message(F.from_user.id != ADMIN_ID)
async def user_any_message(message: Message):
    await message.answer(AUTO_REPLY_TEXT)
    await send_user_message_to_topic(message)

@dp.message(F.chat.id == FORUM_CHAT_ID)
async def admin_from_forum(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    topic_id = message.message_thread_id
    if not topic_id:
        return

    user_id = db_get_user(topic_id)
    if not user_id:
        await message.reply("❌ Bu konuya bağlı kullanıcı bulunamadı.")
        return

    await bot.copy_message(
        chat_id=user_id,
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )

async def main():
    db_init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
