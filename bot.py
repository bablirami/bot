import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from datetime import datetime, timedelta
import logging

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Базовые переменные
CHANNEL_ID = "XCrypto_Pulse"
CHAT_ID = "-f0oeYDCyTAMwM2Ni"
ADMIN_ID = 962267965

# Структура данных для хранения информации о пользователях
users_data = {}

# Функция для инициализации данных пользователя, если его нет
def initialize_user(user_id, first_name):
    if user_id not in users_data:
        users_data[user_id] = {
            "points": 0,
            "last_claim": None,
            "streak": 0,
            "name": first_name,
            "subscribed": False  # Отслеживание подписки
        }

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
        if referrer_id in users_data:
            users_data[referrer_id]["points"] += 100
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

# Команда для получения поинтов и ежедневной награды
async def my_points(update: Update, context):
    user = update.effective_user
    user_id = user.id

    initialize_user(user_id, user.first_name)

    # Получаем данные пользователя
    user_info = users_data[user_id]

    # Рассчитываем текущую дату
    today = datetime.now().date()

    # Проверяем, получал ли пользователь награду сегодня
    if user_info["last_claim"] == today:
        await update.callback_query.message.reply_text("🎁 Ты уже получил свою ежедневную награду сегодня! Возвращайся завтра за следующей наградой. 😉")
    else:
        # Если не получал награду, начисляем её
        user_info["streak"] = min(user_info["streak"] + 1, 7)
        reward = [50, 70, 100, 120, 150, 180, 200][user_info["streak"] - 1]
        user_info["points"] += reward
        user_info["last_claim"] = today

        await update.callback_query.message.reply_text(f"🎉 Ты получил {reward} поинтов за ежедневный визит! У тебя теперь {user_info['points']} поинтов! 🚀")

# Callback handler для обработки нажатий на кнопки
async def button_handler(update: Update, context):
    query = update.callback_query
    data = query.data

    if data == 'points':
        await my_points(update, context)
    elif data == 'leaders':
        await leaderboard(update, context)
    elif data == 'invite':
        await invite(update, context)
    elif data == 'daily_reward':
        await my_points(update, context)  # Теперь функция покажет сообщение, если награда уже получена
    elif data == 'subscribe':
        await subscribe(update, context)  # Добавим подписку на канал

# Список лидеров
async def leaderboard(update: Update, context):
    user = update.effective_user
    initialize_user(user.id, user.first_name)

    sorted_users = sorted(users_data.items(), key=lambda x: x[1]['points'], reverse=True)
    
    leaderboard_text = "🏆 Топ лидеров:\n"
    user_info = users_data[user.id]
    user_position = None

    for i, (user_id, user_data) in enumerate(sorted_users):
        if i < 10:
            leaderboard_text += f"{i + 1}. {user_data['name']}: {user_data['points']} поинтов\n"
        elif user_id == user.id:
            user_position = f"{i + 1}. {user_data['name']}: {user_data['points']} поинтов"

    if user_position:
        leaderboard_text += f"\n👤 Твоя позиция: {user_position}"

    await update.callback_query.message.reply_text(leaderboard_text)

# Функция для генерации реферальной ссылки
async def invite(update: Update, context):
    user = update.effective_user
    user_id = user.id

    initialize_user(user_id, user.first_name)
    
    # Создание реферальной ссылки
    ref_link = f"https://t.me/{CHANNEL_ID}?start={user_id}"
    await update.callback_query.message.reply_text(f"👥 Пригласи друзей и получи 100 поинтов за каждого! Вот твоя реферальная ссылка: {ref_link} 📲")

# Начисление поинтов за подписку на канал
async def subscribe(update: Update, context):
    user = update.effective_user
    user_id = user.id

    initialize_user(user_id, user.first_name)

    user_info = users_data[user_id]
    
    # Проверка, подписан ли уже пользователь
    if user_info.get("subscribed", False):
        await update.callback_query.message.reply_text("👍 Ты уже подписан на наш канал и получил свои 100 поинтов.")
    else:
        user_info["points"] += 100
        user_info["subscribed"] = True  # Отметим, что пользователь подписался
        await update.callback_query.message.reply_text(f"Спасибо за подписку! 🎉 Ты получил 100 поинтов! У тебя теперь {user_info['points']} поинтов.")

# Админ команда для просмотра всех пользователей с ID
async def admin(update: Update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ У вас нет прав для выполнения этой команды.")

    user_list = "\n".join([f"{user_data['name']} (ID: {user_id}): {user_data['points']} поинтов"
                           for user_id, user_data in users_data.items()])
    await update.message.reply_text(f"Список пользователей:\n{user_list}")

# Админ команда для сброса всех поинтов и уведомления всех пользователей
async def reset(update: Update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ У вас нет прав для выполнения этой команды.")
    
    # Сбрасываем все очки и стрики
    for user_id in users_data:
        users_data[user_id]['points'] = 0
        users_data[user_id]['streak'] = 0
        users_data[user_id]['last_claim'] = None

    await update.message.reply_text("🔄 Все очки сброшены.")

    # Рассылаем всем пользователям уведомление о завершении сезона
    for user_id in users_data:
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
        return await update.message.reply_text("Используйте: /add <user_id> <points>.")

    user_id = int(context.args[0])
    points = int(context.args[1])

    if user_id in users_data:
        users_data[user_id]['points'] += points
        await update.message.reply_text(f"✅ {points} поинтов добавлены пользователю {users_data[user_id]['name']}.")
    else:
        await update.message.reply_text("Пользователь не найден.")

# Callback handler для обработки нажатий на кнопки
async def button_handler(update: Update, context):
    query = update.callback_query
    data = query.data

    if data == 'points':
        await my_points(update, context)
    elif data == 'leaders':
        await leaderboard(update, context)
    elif data == 'invite':
        await invite(update, context)
    elif data == 'daily_reward':
        await my_points(update, context)  # Используем ту же функцию для ежедневной награды
    elif data == 'subscribe':
        await subscribe(update, context)  # Добавим подписку на канал

# Основной код для запуска бота
def main():
    application = Application.builder().token("7922474170:AAFLBMg9p1za9VSTeK5cc6BubEmpX_JcWGQ").build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("greet_new_user", greet_new_user))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("add", add_points))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
