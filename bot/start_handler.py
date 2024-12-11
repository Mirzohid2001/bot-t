# start_handler.py
import logging
import requests
import telegram
from requests.exceptions import RequestException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# Logging setup
logger = logging.getLogger(__name__)

# Backend API URL
BACKEND_API_BASE_URL = "http://localhost:8000/blog"  # Backend server URL (adjust as needed)

# States
START, AGREEMENTS = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Start command handler. Shows the 'Start' button for new users to register.
    """
    user = update.effective_user
    keyboard = [[InlineKeyboardButton("Начать", callback_data="register")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Добро пожаловать! Нажмите кнопку 'Начать' для продолжения.",
        reply_markup=reply_markup
    )
    return START

async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Register the user by sending a request to the backend API.
    """
    query = update.callback_query
    await query.answer()  # Acknowledge the button press
    user = query.from_user
    api_url = f"{BACKEND_API_BASE_URL}/register/"
    data = {"telegram_id": user.id, "username": user.username}

    try:
        response = requests.post(api_url, json=data)
        response.raise_for_status()
        await safe_edit_message_text(
            query,
            "Пользователь успешно зарегистрирован."
        )
        return await check_agreements(query, context)
    except RequestException as e:
        logger.error(f"Error registering user: {e}")
        await safe_edit_message_text(
            query,
            "Произошла ошибка при регистрации. Попробуйте еще раз позже."
        )
        return ConversationHandler.END

async def check_agreements(query, context: ContextTypes.DEFAULT_TYPE):
    """
    Check user agreements and guide to acceptance if needed.
    """
    user = query.from_user
    api_url = f"{BACKEND_API_BASE_URL}/consent-status/{user.id}/"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        consent_data = response.json()
        if consent_data.get('consent_given', False):
            await safe_edit_message_text(
                query,
                "Ваше согласие уже получено. Можете продолжить."
            )
            # Show the subscription menu if consent is already given
            await show_subscription_menu(query)
            return ConversationHandler.END
        else:
            keyboard = [[
                InlineKeyboardButton("Принять", callback_data="accept_user_agreement"),
                InlineKeyboardButton("Отказаться", callback_data="reject_user_agreement")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await safe_edit_message_text(
                query,
                "Для продолжения необходимо принять пользовательское соглашение.",
                reply_markup=reply_markup
            )
            return AGREEMENTS
    except RequestException as e:
        logger.error(f"Error checking user agreements: {e}")
        await safe_edit_message_text(
            query,
            "Произошла ошибка при проверке соглашений. Попробуйте позже."
        )
        return ConversationHandler.END

async def handle_agreement_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Acknowledge the button press
    action = query.data

    if action == "accept_user_agreement":
        user = query.from_user
        api_url = f"{BACKEND_API_BASE_URL}/consent/{user.id}/"
        data = {"consent_given": True}

        try:
            response = requests.post(api_url, json=data)
            response.raise_for_status()

            # Rozilik berilganidan keyin yangi menyu chiqariladi
            await query.message.reply_text("Согласие принято. Спасибо!")
            await show_subscription_menu(query)
            return ConversationHandler.END
        except RequestException as e:
            logger.error(f"Error saving user agreement: {e}")
            await query.edit_message_text(
                "Произошла ошибка при сохранении согласия. Попробуйте позже."
            )
            return ConversationHandler.END
    elif action == "reject_user_agreement":
        await query.edit_message_text(
            "Без принятия пользовательского соглашения нельзя продолжить."
        )
        return ConversationHandler.END

    return AGREEMENTS

async def show_subscription_menu(query):
    """
    Show the subscription menu to the user.
    """
    keyboard = [
        [
            InlineKeyboardButton("Приобрести подписку", callback_data="select_plan"),
            InlineKeyboardButton("Подарить подписку", callback_data="gift_subscription"),
        ],
        [
            InlineKeyboardButton("Поддержка", callback_data="support"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "Пожалуйста, выберите одно из следующих действий:",
        reply_markup=reply_markup
    )

async def safe_edit_message_text(query, new_text, reply_markup=None):
    """
    Edit a message's text safely by checking if the new text is different from the current one.
    """
    try:
        if query.message.text != new_text:
            await query.edit_message_text(text=new_text, reply_markup=reply_markup)
    except telegram.error.BadRequest as e:
        if "Message is not modified" not in str(e):
            raise