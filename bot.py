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
import requests
from PIL import Image

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

# База данных
conn = sqlite3.connect('memory.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS chats 
             (user_id INTEGER, message TEXT, response TEXT, date TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS user_data 
             (user_id INTEGER PRIMARY KEY, name TEXT, mood TEXT, last_photo TEXT)''')
conn.commit()

# Имя девушки (замени на ее имя)
GIRL_NAME = "Аня"

# Комплименты
MORNING_COMPLIMENTS = [
    f"Доброе утро, {GIRL_NAME}! Ты сегодня прекрасна как никогда ☀️",
    f"Просыпайся, {GIRL_NAME}! Твой личный бот уже скучает 💕",
    f"С добрым утром! Твоя улыбка освещает мир сильнее солнца ✨",
    f"Самый лучший человек просыпается! Люблю тебя 💖",
    f"Новый день — новая возможность быть счастливой. Ты справишься! 🌸"
]

# Пути для моделей
os.makedirs("models", exist_ok=True)
os.makedirs("generated", exist_ok=True)

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(f"👋 Привет! Я персональный бот для {GIRL_NAME}. Говори что хочешь — я запоминаю и учусь.\n\n"
                         f"Команды:\n"
                         f"/compliment - получить комплимент\n"
                         f"/mood [текст] - рассказать о настроении\n"
                         f"/remember - что я помню о тебе")

@dp.message(Command("compliment"))
async def compliment(message: Message):
    await message.answer(random.choice(MORNING_COMPLIMENTS))

@dp.message(Command("mood"))
async def set_mood(message: Message):
    mood_text = message.text.replace("/mood", "").strip()
    if mood_text:
        user_id = message.from_user.id
        c.execute("INSERT OR REPLACE INTO user_data (user_id, mood) VALUES (?, ?)", 
                  (user_id, mood_text))
        conn.commit()
        await message.answer(f"Запомнил твое настроение: {mood_text} 💭")
    else:
        await message.answer("Напиши свое настроение после /mood, например: /mood сегодня грустно")

@dp.message(Command("remember"))
async def remember(message: Message):
    user_id = message.from_user.id
    c.execute("SELECT mood FROM user_data WHERE user_id=?", (user_id,))
    data = c.fetchone()
    
    if data and data[0]:
        await message.answer(f"Я помню:\nНастроение: {data[0]}")
    else:
        await message.answer("Я пока ничего о тебе не запомнил. Расскажи о себе через /mood")

@dp.message()
async def chat(message: Message):
    user_id = message.from_user.id
    text = message.text
    
    if not text:
        return
    
    # Если прислали фото
    if message.photo:
        await message.answer("📸 Ты прекрасна на этом фото! ✨")
        return
    
    # Обычный диалог через OpenRouter
    try:
        # Получаем последние сообщения для контекста
        c.execute("SELECT message, response FROM chats WHERE user_id=? ORDER BY date DESC LIMIT 5", (user_id,))
        history = c.fetchall()
        
        messages = []
        for msg, resp in reversed(history):
            messages.append({"role": "user", "content": msg})
            messages.append({"role": "assistant", "content": resp})
        
        messages.append({"role": "user", "content": text})
        
        response = await client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=messages,
            temperature=0.8
        )
        answer = response.choices[0].message.content
        
        # Сохраняем в память
        c.execute("INSERT INTO chats VALUES (?, ?, ?, ?)",
                  (user_id, text, answer, str(datetime.now())))
        conn.commit()
        
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

async def send_morning_compliment():
    chat_id = os.getenv("GIRL_CHAT_ID")
    if chat_id:
        try:
            compliment = random.choice(MORNING_COMPLIMENTS)
            await bot.send_message(chat_id, compliment)
            print(f"✅ Утренний комплимент отправлен {chat_id}")
        except Exception as e:
            print(f"❌ Ошибка отправки комплимента: {e}")

async def send_test_message():
    """Тестовая отправка через 2 минуты после запуска"""
    await asyncio.sleep(120)
    chat_id = os.getenv("GIRL_CHAT_ID")
    if chat_id:
        try:
            await bot.send_message(chat_id, "🔔 Тест! Если видишь это - бот работает и утренние комплименты будут приходить 👌")
            print("✅ Тест отправлен")
        except Exception as e:
            print(f"❌ Ошибка теста: {e}")

async def main():
    # Планировщик для утренних комплиментов
    scheduler.add_job(send_morning_compliment, 'cron', hour=8, minute=0)
    scheduler.start()
    
    # Запускаем тест через 2 минуты
    asyncio.create_task(send_test_message())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
