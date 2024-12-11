from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
import asyncio
import sqlite3
import logging

# Инициализация бота и логгера
API_TOKEN = '7581719295:AAF-cZYSr7Eq-kzLOXchB5Cms2fhycC2aO8'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# Инициализация базы данных
conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    answer TEXT NOT NULL,
    FOREIGN KEY(question_id) REFERENCES questions(id)
)''')

conn.commit()

# Состояния
admin_mode = False
current_questions = {}

# Команда /start
@dp.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM questions")
    questions = cursor.fetchall()

    if not questions:
        await message.answer("Привет! Вопросов пока нет.")
    else:
        current_questions[user_id] = iter(questions)
        await ask_next_question(message)

def save_answer(user_id, question_id, answer):
    cursor.execute(
        "INSERT INTO answers (user_id, question_id, answer) VALUES (?, ?, ?)",
        (user_id, question_id, answer)
    )
    conn.commit()

async def ask_next_question(message):
    user_id = message.from_user.id
    questions_iter = current_questions.get(user_id)

    try:
        question = next(questions_iter)
        await message.answer(question[1])
    except StopIteration:
        del current_questions[user_id]
        await message.answer("Спасибо за ответы!")

# Обработка текста
@dp.message()
async def handle_text(message: Message):
    global admin_mode

    if admin_mode and message.text.lower() == "cancel_admin_sage_mode":
        admin_mode = False
        await message.answer("Вы вышли из режима администратора.")
        return

    if message.text.lower() == "admin_sage_mode":
        admin_mode = True
        await message.answer("Вы вошли в режим администратора. Введите вопросы по одному, завершите командой cancel_admin_sage_mode.")
        return

    if admin_mode:
        cursor.execute("INSERT INTO questions (question) VALUES (?)", (message.text,))
        conn.commit()
        await message.answer(f"Вопрос сохранен: {message.text}")
        return

    if message.text.lower() == "admin_answers":
        cursor.execute("SELECT user_id, question, answer FROM answers JOIN questions ON answers.question_id = questions.id")
        rows = cursor.fetchall()

        report = "Отчёт по ответам:\n"
        for row in rows:
            report += f"Пользователь {row[0]} ответил на вопрос '{row[1]}': {row[2]}\n"

        await message.answer(report, parse_mode=ParseMode.HTML)
        return

    user_id = message.from_user.id
    if user_id in current_questions:
        questions_iter = current_questions[user_id]
        question = next(questions_iter, None)

        if question:
            save_answer(user_id, question[0], message.text)
            await ask_next_question(message)
        else:
            await message.answer("Спасибо за ответы!")
    else:
        await message.answer("Неизвестная команда или завершены ответы на вопросы.")

async def main():
    dp.include_router(dp)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
