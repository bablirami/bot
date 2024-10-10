import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from datetime import datetime
import logging

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Базовые переменные
CHANNEL_ID = "XCrypto_Pulse"
ADMIN_ID = 962267965

# Подключение к базе данных
conn = sqlite3.connect("bot_users.db")
cursor = conn.cursor()

# Создание таблицы пользователей, если она не существует
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    points INTEGER DEFAULT 0,
    last_claim TEXT,
    streak INTEGER DEFAULT 0,
    subscribed INTEGER DEFAULT 0
)''')
conn.commit()

# Функция для инициализации данных пользователя
def initialize_user(user_id, first_name):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)", (user_id, first_name))
    conn.commit()

# Функция для приветствия новых пользователей
async def greet_new_user(update: Update, context):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name

    initialize_user(user_id, first_name)
    await update.message.reply_text(f"👋 Привет, {first_name}! Добро пожаловать в наш канал! 🎉 Рад видеть тебя здесь! 🚀")

# Функция для старта
async def start(update: Update, context):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name

    # Проверяем, был ли новый пользователь приглашен через реферальную ссылку
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (referrer_id,))
        referrer = cursor.fetchone()
        if referrer:
            new_points = referrer[2] + 100
            cursor.execute("UPDATE users SET points = ? WHERE user_id = ?", (new_points, referrer_id))
            conn.commit()
            await context.bot.send_message(chat_id=referrer_id, text="🎉 Ваш друг присоединился! Вы получили 100 поинтов! 🎉")

    initialize_user(user_id, first_name)

    keyboard = [
        [InlineKeyboardButton("📊 Мои поинты", callback_data='points')],
        [InlineKeyboardButton("🏆 Список лидеров", callback_data='leaders')],
        [InlineKeyboardButton("👥 Пригласить друзей", callback_data='invite')],
        [InlineKeyboardButton("🎁 Ежедневная награда", callback_data='daily_reward')],
        [InlineKeyboardButton("💬 Подпишись на наш канал", url=f"https://t.me/{CHANNEL_ID}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f"Добро пожаловать, {first_name}! 🥳\nЧто хочешь сделать? 👇", reply_markup=reply_markup)

# Команда для получения поинтов
async def my_points(update: Update, context):
    user = update.effective_user
    user_id = user.id

    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    user_info = cursor.fetchone()

    if user_info:
        await update.callback_query.message.reply_text(f"🎉 У тебя {user_info[0]} поинтов! 🚀")
    else:
        await update.callback_query.message.reply_text("❌ Ошибка: пользователь не найден в базе данных.")

# Команда для ежедневной награды
async def daily_reward(update: Update, context):
    user = update.effective_user
    user_id = user.id

    cursor.execute("SELECT points, last_claim, streak FROM users WHERE user_id = ?", (user_id,))
    user_info = cursor.fetchone()

    if user_info:
        today = datetime.now().date()
        last_claim_date = datetime.strptime(user_info[1], "%Y-%m-%d").date() if user_info[1] else None
        
        if last_claim_date == today:
            await update.callback_query.message.reply_text("🎁 Ты уже получил свою ежедневную награду сегодня! Возвращайся завтра за следующей наградой. 😉")
        else:
            streak = min(user_info[2] + 1, 7)
            reward = [50, 70, 100, 120, 150, 180, 200][streak - 1]
            new_points = user_info[0] + reward
            
            cursor.execute("UPDATE users SET points = ?, last_claim = ?, streak = ? WHERE user_id = ?", 
                           (new_points, today, streak, user_id))
            conn.commit()

            await update.callback_query.message.reply_text(f"🎉 Ты получил {reward} поинтов за ежедневный визит! У тебя теперь {new_points} поинтов! 🚀")
    else:
        await update.callback_query.message.reply_text("❌ Ошибка: пользователь не найден в базе данных.")

# Список лидеров
async def leaderboard(update: Update, context):
    user = update.effective_user
    initialize_user(user.id, user.first_name)

    cursor.execute("SELECT user_id, first_name, points FROM users ORDER BY points DESC LIMIT 10")
    top_users = cursor.fetchall()

    leaderboard_text = "🏆 Топ лидеров:\n"
    user_position = None

    for i, (user_id, first_name, points) in enumerate(top_users):
        leaderboard_text += f"{i + 1}. {first_name}: {points} поинтов\n"
        if user_id == user.id:
            user_position = f"👤 Твоя позиция: {i + 1}. {first_name}: {points} поинтов"

    if user_position:
        leaderboard_text += f"\n{user_position}"

    await update.callback_query.message.reply_text(leaderboard_text)

# Функция для генерации реферальной ссылки
async def invite(update: Update, context):
    user = update.effective_user
    user_id = user.id

    initialize_user(user_id, user.first_name)
    
    # Создание реферальной ссылки
    ref_link = f"https://t.me/{CHANNEL_ID}?start={user_id}"
    await update.callback_query.message.reply_text(f"👥 Пригласи друзей и получи 100 поинтов за каждого! Вот твоя реферальная ссылка: {ref_link} 📲")

# Админ команда для просмотра всех пользователей с ID
async def admin(update: Update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ У вас нет прав для выполнения этой команды.")

    cursor.execute("SELECT user_id, first_name, points FROM users")
    users_list = cursor.fetchall()
    user_list = "\n".join([f"{first_name} (ID: {user_id}): {points} поинтов" for user_id, first_name, points in users_list])
    await update.message.reply_text(f"Список пользователей:\n{user_list}")

# Админ команда для сброса всех поинтов и уведомления всех пользователей
async def reset(update: Update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ У вас нет прав для выполнения этой команды.")
    
    # Сбрасываем все очки и стрики
    cursor.execute("UPDATE users SET points = 0, streak = 0, last_claim = NULL")
    conn.commit()

    await update.message.reply_text("🔄 Все очки сброшены.")

    # Рассылаем всем пользователям уведомление о завершении сезона
    cursor.execute("SELECT user_id FROM users")
    users_list = cursor.fetchall()
    for user_id, in users_list:
        try:
            await context.bot.send_message(chat_id=user_id, text="🎉 Сезон окончен! Забирай свои призы и готовься к новому сезону!")
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

# Админ команда добавления поинтов
async def add_points(update: Update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ У вас нет прав для выполнения этой команды.")

    if len(context.args) != 2 or not context.args[0].isdigit() or not context.args[1].isdigit():
        return await update.message.reply_text("⚠️ Используйте: /add <user_id> <points>")

    user_id = int(context.args[0])
    points_to_add = int(context.args[1])

    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points_to_add, user_id))
    conn.commit()

    await update.message.reply_text(f"✅ Успешно добавлено {points_to_add} поинтов пользователю с ID {user_id}.")

# Обработчик нажатий кнопок
async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'points':
        await my_points(update, context)
    elif query.data == 'daily_reward':
        await daily_reward(update, context)
    elif query.data == 'leaders':
        await leaderboard(update, context)
    elif query.data == 'invite':
        await invite(update, context)

# Основная функция для запуска бота
def main():
    application = Application.builder().token("7626312484:AAHQBrzw6nu0F4_EZfe55LhtztaF5RP2Wds").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("add", add_points))
    application.add_handler(CommandHandler("greet", greet_new_user))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_polling()

if __name__ == "__main__":
    main()
