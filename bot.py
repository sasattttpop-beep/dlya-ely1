import asyncio
import logging
import sqlite3
import os
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
from openai import AsyncOpenAI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

conn = sqlite3.connect('memory.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS chats 
             (user_id INTEGER, message TEXT, response TEXT, date TEXT)''')
conn.commit()

GIRL_NAME = "Аня"

MORNING_COMPLIMENTS = [
    f"Доброе утро, {GIRL_NAME}! Ты сегодня прекрасна ☀️",
    f"Просыпайся, {GIRL_NAME}! Бот скучает 💕",
    f"С добрым утром! Твоя улыбка освещает мир ✨",
]

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(f"👋 Привет! Я бот для {GIRL_NAME}")

@dp.message(Command("compliment"))
async def compliment(message: Message):
    await message.answer(random.choice(MORNING_COMPLIMENTS))

@dp.message()
async def chat(message: Message):
    text = message.text
    if not text:
        return
    
    try:
        response = await client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[{"role": "user", "content": text}]
        )
        answer = response.choices[0].message.content
        
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

async def send_morning_compliment():
    chat_id = os.getenv("GIRL_CHAT_ID")
    if chat_id:
        try:
            await bot.send_message(chat_id, random.choice(MORNING_COMPLIMENTS))
        except:
            pass

async def send_test_message():
    await asyncio.sleep(120)
    chat_id = os.getenv("GIRL_CHAT_ID")
    if chat_id:
        try:
            await bot.send_message(chat_id, "🔔 Тест! Бот работает")
        except:
            pass

async def main():
    scheduler.add_job(send_morning_compliment, 'cron', hour=8, minute=0)
    scheduler.start()
    asyncio.create_task(send_test_message())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
