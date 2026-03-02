import asyncio
import logging
import sqlite3
import os
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from dotenv import load_dotenv
from openai import AsyncOpenAI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import requests
from elevenlabs import generate, set_api_key
import torch
from diffusers import StableDiffusionPipeline
from PIL import Image

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

# ElevenLabs
set_api_key(ELEVENLABS_KEY)

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

# Пути для моделей (создай папки)
os.makedirs("models", exist_ok=True)
os.makedirs("generated", exist_ok=True)
os.makedirs("voice", exist_ok=True)

# Загрузка модели для генерации фото (будет позже)
# pipe = None

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(f"👋 Привет! Я персональный бот для {GIRL_NAME}. Говори что хочешь — я запоминаю и учусь.\n\n"
                         f"Команды:\n"
                         f"/compliment - получить комплимент\n"
                         f"/mood [текст] - рассказать о настроении\n"
                         f"/voice [текст] - озвучить текст голосом\n"
                         f"/photo [запрос] - сгенерировать фото\n"
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

@dp.message(Command("voice"))
async def voice_message(message: Message):
    text = message.text.replace("/voice", "").strip()
    if not text:
        await message.answer("Напиши текст после /voice")
        return
    
    try:
        # Генерация голоса через ElevenLabs
        audio = generate(
            text=text,
            voice="Bella",  # Можно заменить на клонированный голос
            model="eleven_monolingual_v1"
        )
        
        # Сохраняем и отправляем
        audio_path = f"voice/msg_{datetime.now().timestamp()}.mp3"
        with open(audio_path, "wb") as f:
            f.write(audio)
        
        await message.answer_voice(FSInputFile(audio_path))
        os.remove(audio_path)
    except Exception as e:
        await message.answer(f"Ошибка генерации голоса: {e}")

@dp.message(Command("photo"))
async def generate_photo(message: Message):
    prompt = message.text.replace("/photo", "").strip()
    if not prompt:
        await message.answer("Напиши запрос после /photo, например: /photo девушка в космосе")
        return
    
    await message.answer("🖼️ Генерирую фото... это займет около минуты")
    
    try:
        # Здесь будет LoRA модель с ее лицом
        # Пока просто заглушка
        await asyncio.sleep(2)
        await message.answer("⚠️ Модуль генерации фото настраивается. Нужно обучить модель на ее фото.")
        
        # Когда обучишь LoRA:
        # image = pipe(prompt + " mygirl").images[0]
        # image.save(f"generated/photo_{datetime.now().timestamp()}.png")
        # await message.answer_photo(FSInputFile(f"generated/photo_{datetime.now().timestamp()}.png"))
    except Exception as e:
        await message.answer(f"Ошибка генерации: {e}")

@dp.message(Command("remember"))
async def remember(message: Message):
    user_id = message.from_user.id
    c.execute("SELECT mood, last_photo FROM user_data WHERE user_id=?", (user_id,))
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
    
    # Анализ фото, если прислали
    if message.photo:
        await message.answer("📸 Обрабатываю фото...")
        # Здесь будет анализ эмоций
        await message.answer("Ты прекрасна на этом фото! ✨")
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
    # Здесь должен быть ID чата с девушкой
    # Пока просто заглушка
    chat_id = os.getenv("GIRL_CHAT_ID")
    if chat_id:
        try:
            compliment = random.choice(MORNING_COMPLIMENTS)
            await bot.send_message(chat_id, compliment)
            
            # Можно добавить музыку
            # await bot.send_audio(chat_id, FSInputFile("music/morning_song.mp3"))
        except:
            pass

async def main():
    # Планировщик для утренних комплиментов
    scheduler.add_job(send_morning_compliment, 'cron', hour=8, minute=0)
    scheduler.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
