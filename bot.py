import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
import os
from openai import AsyncOpenAI

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

conn = sqlite3.connect('memory.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS chats 
             (user_id INTEGER, message TEXT, response TEXT, date TEXT)''')
conn.commit()

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("👋 Привет! Я твой персональный бот. Говори что хочешь — я запоминаю и учусь.")

@dp.message()
async def chat(message: Message):
    user_id = message.from_user.id
    text = message.text
    
    try:
        response = await client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[{"role": "user", "content": text}]
        )
        answer = response.choices[0].message.content
        
        c.execute("INSERT INTO chats VALUES (?, ?, ?, ?)",
                  (user_id, text, answer, str(datetime.now())))
        conn.commit()
        
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

async def morning_task():
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            # TODO: утренняя рассылка
            pass
        await asyncio.sleep(60)

async def main():
    asyncio.create_task(morning_task())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
