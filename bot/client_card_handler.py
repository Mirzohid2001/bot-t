# client_card_handler.py
import logging
import requests
from requests.exceptions import RequestException
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CommandHandler
)

# Logging setup
logger = logging.getLogger(__name__)

# Backend API URL
BACKEND_API_BASE_URL = "http://localhost:8000/blog"  # Adjust as needed

# States for client card flow
FILL_CARD_NAME, FILL_CARD_AGE, FILL_CARD_GOALS, FILL_CARD_CHALLENGES = range(4)

async def start_filling_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Start the process of filling out the client's card.
    """
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("Пожалуйста, введите ваше имя:")
        return FILL_CARD_NAME

async def fill_card_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the user's input for their name.
    """
    context.user_data["client_card_name"] = update.message.text

    # Add "Назад" button
    keyboard = [[InlineKeyboardButton("Назад", callback_data="go_back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_chat.send_message("Пожалуйста, введите ваш возраст:", reply_markup=reply_markup)
    return FILL_CARD_AGE

async def fill_card_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the user's input for their age.
    """
    context.user_data["client_card_age"] = update.message.text

    # Add "Назад" button
    keyboard = [[InlineKeyboardButton("Назад", callback_data="go_back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_chat.send_message("Пожалуйста, опишите ваши цели:", reply_markup=reply_markup)
    return FILL_CARD_GOALS

async def fill_card_goals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the user's input for their goals.
    """
    context.user_data["client_card_goals"] = update.message.text

    # Add "Назад" button
    keyboard = [[InlineKeyboardButton("Назад", callback_data="go_back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_chat.send_message("Пожалуйста, опишите ваши трудности:", reply_markup=reply_markup)
    return FILL_CARD_CHALLENGES

async def fill_card_challenges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the user's input for their challenges and save the client card.
    """
    context.user_data["client_card_challenges"] = update.message.text

    # Prepare card data
    user = update.message.from_user
    api_url = f"{BACKEND_API_BASE_URL}/client-cards/{user.id}/"
    data = {
        "name": context.user_data.get("client_card_name"),
        "age": context.user_data.get("client_card_age"),
        "goals": context.user_data.get("client_card_goals"),
        "challenges": context.user_data.get("client_card_challenges"),
    }

    try:
        response = requests.post(api_url, json=data)
        response.raise_for_status()

        # Display the saved card information
        card_info = (
            f"Имя: {data['name']}\n"
            f"Возраст: {data['age']}\n"
            f"Цели: {data['goals']}\n"
            f"Трудности: {data['challenges']}"
        )

        await update.effective_chat.send_message("Ваша карта успешно сохранена!")
        await update.effective_chat.send_message(f"Ваша карта:\n{card_info}")

        # Show main menu
        await show_main_menu(update, context)

        return ConversationHandler.END

    except RequestException as e:
        logger.error(f"Error saving client card: {e}")
        await update.effective_chat.send_message("Произошла ошибка при сохранении карты. Попробуйте позже.")
        return ConversationHandler.END

async def get_client_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Fetch and display the client's card information.
    """
    user = update.effective_user
    api_url = f"{BACKEND_API_BASE_URL}/client-cards/{user.id}/"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        card_data = response.json()

        card_info = (
            f"Имя: {card_data['name']}\n"
            f"Возраст: {card_data['age']}\n"
            f"Цели: {card_data['goals']}\n"
            f"Трудности: {card_data['challenges']}"
        )

        await update.effective_chat.send_message(f"Ваша карта:\n{card_info}")

        # Show main menu
        await show_main_menu(update, context)

    except RequestException as e:
        logger.error(f"Error fetching client card: {e}")
        await update.effective_chat.send_message("Произошла ошибка при получении карты. Попробуйте позже.")

async def go_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle 'Назад' button to return to the main menu.
    """
    query = update.callback_query
    await query.answer()
    await show_main_menu(update, context)
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show the main menu.
    """
    keyboard = [
        [InlineKeyboardButton("Заполнить карту", callback_data="fill_card")],
        [InlineKeyboardButton("Пройти сеанс", callback_data="start_session")],
        [InlineKeyboardButton("Материалы", callback_data="materials")],
        [InlineKeyboardButton("Пополнить баланс", callback_data="recharge_balance")],
        [InlineKeyboardButton("Подарить подписку", callback_data="gift_subscription")],
        [InlineKeyboardButton("Мой аккаунт", callback_data="my_account")],
        [InlineKeyboardButton("Обратная связь", callback_data="feedback")],
        [InlineKeyboardButton("Поддержка", callback_data="support")],
        [InlineKeyboardButton("Назад", callback_data="go_back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text("Пожалуйста, выберите действие:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Пожалуйста, выберите действие:", reply_markup=reply_markup)

# Conversation handler for filling client card
client_card_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_filling_card, pattern="^fill_card$")],
    states={
        FILL_CARD_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, fill_card_name),
            CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$")
        ],
        FILL_CARD_AGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, fill_card_age),
            CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$")
        ],
        FILL_CARD_GOALS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, fill_card_goals),
            CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$")
        ],
        FILL_CARD_CHALLENGES: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, fill_card_challenges),
            CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$")
        ],
    },
    fallbacks=[CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$")],
)

# Add handler to fetch client card
get_client_card_handler = CommandHandler("get_card", get_client_card)
