# subscription_handler.py
import logging
import requests
from requests.exceptions import RequestException
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
import httpx

# Импорт необходимых функций из other_handlers.py
from other_handlers import show_main_menu, go_back_to_menu

# Настройка логирования
logger = logging.getLogger(__name__)

# URL API бэкенда
BACKEND_API_BASE_URL = "http://localhost:8000/blog"  # Настройте при необходимости

# -------------------------------
# Определение состояний для ConversationHandler
# -------------------------------
SELECT_PLAN, SELECT_PAYMENT_METHOD, ENTER_PAYMENT_DETAILS, \
SELECT_GIFT_RECIPIENT, SELECT_GIFT_PLAN, SELECT_GIFT_PAYMENT_METHOD, \
ENTER_GIFT_PAYMENT_DETAILS, SHOW_FAQ, SHOW_FAQ_ANSWER, SEND_SUPPORT_MESSAGE = range(10)

# -------------------------------
# Функции для подписки
# -------------------------------

async def show_subscription_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает доступные планы подписки пользователю.
    """
    query = update.callback_query
    await query.answer()

    api_url = f"{BACKEND_API_BASE_URL}/subscription-plans/"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        plans = response.json()

        keyboard = [
            [InlineKeyboardButton(plan["name"], callback_data=f"select_plan_{plan['id']}")]
            for plan in plans
        ]
        keyboard.append([InlineKeyboardButton("Назад", callback_data="go_back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "📋 Пожалуйста, выберите план подписки:", reply_markup=reply_markup
        )
        return SELECT_PLAN
    except RequestException as e:
        logger.error(f"Ошибка при получении планов подписки: {e}")
        await query.edit_message_text("❌ Произошла ошибка при получении планов подписки. Попробуйте позже.")
        return ConversationHandler.END


async def select_subscription_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор пользователем плана подписки и показывает способы оплаты.
    """
    query = update.callback_query
    await query.answer()

    # Извлекаем ID плана из callback_data
    plan_id = query.data.split("_")[-1]
    context.user_data["selected_plan_id"] = plan_id

    api_url = f"{BACKEND_API_BASE_URL}/payment-methods/"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        methods = response.json()

        keyboard = [
            [InlineKeyboardButton(method["name"], callback_data=f"select_method_{method['id']}")]
            for method in methods
        ]
        keyboard.append([InlineKeyboardButton("Назад", callback_data="go_back_to_plans")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "💳 Пожалуйста, выберите способ оплаты:", reply_markup=reply_markup
        )
        return SELECT_PAYMENT_METHOD
    except RequestException as e:
        logger.error(f"Ошибка при получении способов оплаты: {e}")
        await query.edit_message_text("❌ Произошла ошибка при получении способов оплаты. Попробуйте позже.")
        return ConversationHandler.END


async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор пользователем способа оплаты и запрашивает детали оплаты.
    """
    query = update.callback_query
    await query.answer()

    # Извлекаем ID способа оплаты из callback_data
    method_id = query.data.split("_")[-1]
    context.user_data["selected_method_id"] = method_id

    # Кнопка "Назад"
    keyboard = [[InlineKeyboardButton("Назад", callback_data="go_back_to_methods")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("🔒 Пожалуйста, введите номер карты для оплаты:", reply_markup=reply_markup)
    return ENTER_PAYMENT_DETAILS


async def enter_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод деталей оплаты и отправляет данные в бэкенд.
    """
    user = update.message.from_user
    card_number = update.message.text.strip()

    # Проверка валидности номера карты (опционально)
    if not card_number.isdigit() or not (13 <= len(card_number) <= 19):
        await update.message.reply_text("❌ Неверный формат номера карты. Пожалуйста, попробуйте снова.")
        return ENTER_PAYMENT_DETAILS

    # Подготавливаем данные для оплаты
    plan_id = context.user_data.get("selected_plan_id")
    method_id = context.user_data.get("selected_method_id")

    api_url = f"{BACKEND_API_BASE_URL}/make-payment/{user.id}/"
    data = {
        "subscription_plan": plan_id,
        "payment_method": method_id,
        "transaction_id": card_number
    }

    try:
        response = requests.post(api_url, json=data)
        response.raise_for_status()

        # Кнопка "Назад" после успешной оплаты
        keyboard = [
            [InlineKeyboardButton("Назад", callback_data="go_back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("✅ Оплата прошла успешно. Спасибо за покупку подписки!", reply_markup=reply_markup)
        await show_main_menu(update, context)
        return ConversationHandler.END
    except RequestException as e:
        logger.error(f"Ошибка при обработке оплаты: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке оплаты. Попробуйте позже.")
        return ConversationHandler.END

# -------------------------------
# Функции для подарка подписки
# -------------------------------

async def start_gifting_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает процесс подарка подписки, запрашивая username получателя.
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎁 Пожалуйста, введите username пользователя, которому вы хотите подарить подписку (например, @username):"
    )
    return SELECT_GIFT_RECIPIENT


async def select_gift_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод пользователя для получения username получателя и показывает доступные планы подписки.
    """
    recipient_username = update.message.text.strip()
    if not recipient_username.startswith('@') or len(recipient_username) < 2:
        await update.message.reply_text(
            "❌ Неверный формат username. Пожалуйста, введите корректный username, начинающийся с @."
        )
        return SELECT_GIFT_RECIPIENT

    context.user_data["recipient_username"] = recipient_username

    api_url = f"{BACKEND_API_BASE_URL}/subscription-plans/"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        plans = response.json()

        keyboard = [
            [InlineKeyboardButton(plan["name"], callback_data=f"select_gift_plan_{plan['id']}")]
            for plan in plans
        ]
        keyboard.append([InlineKeyboardButton("Назад", callback_data="go_back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🎁 Пожалуйста, выберите план подписки, который вы хотите подарить:",
            reply_markup=reply_markup
        )
        return SELECT_GIFT_PLAN
    except RequestException as e:
        logger.error(f"Ошибка при получении планов подписки: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении планов подписки. Попробуйте позже.")
        return ConversationHandler.END


async def select_gift_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор пользователем плана подписки для подарка и показывает способы оплаты.
    """
    query = update.callback_query
    await query.answer()

    # Извлекаем ID плана из callback_data
    plan_id = query.data.split("_")[-1]
    context.user_data["selected_plan_id"] = plan_id

    api_url = f"{BACKEND_API_BASE_URL}/payment-methods/"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        methods = response.json()

        keyboard = [
            [InlineKeyboardButton(method["name"], callback_data=f"select_gift_method_{method['id']}")]
            for method in methods
        ]
        keyboard.append([InlineKeyboardButton("Назад", callback_data="go_back_to_gift_plans")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "💳 Пожалуйста, выберите способ оплаты:", reply_markup=reply_markup
        )
        return SELECT_GIFT_PAYMENT_METHOD
    except RequestException as e:
        logger.error(f"Ошибка при получении способов оплаты: {e}")
        await query.edit_message_text("❌ Произошла ошибка при получении способов оплаты. Попробуйте позже.")
        return ConversationHandler.END


async def select_gift_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор пользователем способа оплаты для подарка и запрашивает детали оплаты.
    """
    query = update.callback_query
    await query.answer()

    # Извлекаем ID способа оплаты из callback_data
    method_id = query.data.split("_")[-1]
    context.user_data["selected_method_id"] = method_id

    # Кнопка "Назад"
    keyboard = [[InlineKeyboardButton("Назад", callback_data="go_back_to_gift_methods")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("🔒 Пожалуйста, введите номер карты для оплаты:", reply_markup=reply_markup)
    return ENTER_GIFT_PAYMENT_DETAILS


async def enter_gift_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод деталей оплаты для подарка и отправляет данные в бэкенд.
    """
    user = update.message.from_user
    card_number = update.message.text.strip()

    # Проверка валидности номера карты (опционально)
    if not card_number.isdigit() or not (13 <= len(card_number) <= 19):
        await update.message.reply_text("❌ Неверный формат номера карты. Пожалуйста, попробуйте снова.")
        return ENTER_GIFT_PAYMENT_DETAILS

    # Подготавливаем данные для подарка подписки
    recipient_username = context.user_data.get("recipient_username")
    plan_id = context.user_data.get("selected_plan_id")
    method_id = context.user_data.get("selected_method_id")
    api_url = f"{BACKEND_API_BASE_URL}/gift-subscription/{user.id}/"
    data = {
        "subscription_plan": plan_id,
        "payment_method": method_id,
        "recipient_username": recipient_username,
        "transaction_id": card_number  # Используем номер карты как временный ID транзакции
    }

    try:
        response = requests.post(api_url, json=data)
        response.raise_for_status()

        # Кнопка "Назад" после успешного подарка
        keyboard = [
            [InlineKeyboardButton("Назад", callback_data="go_back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"🎁 Подписка успешно подарена пользователю {recipient_username}! Спасибо за использование нашего сервиса.",
            reply_markup=reply_markup
        )
        await show_main_menu(update, context)
        return ConversationHandler.END
    except RequestException as e:
        logger.error(f"Ошибка при отправке подарка подписки: {e}")
        await update.message.reply_text("❌ Произошла ошибка при отправке подарка. Попробуйте позже.")
        return ConversationHandler.END

# -------------------------------
# Функции для поддержки
# -------------------------------

# Предполагается, что FAQ_ITEMS определены в other_handlers.py
# Если они определены там, убедитесь, что можно импортировать их сюда
# Для примера, определим их здесь

FAQ_ITEMS = [
    {
        "question": "Как пополнить баланс?",
        "answer": "Вы можете пополнить баланс, выбрав опцию 'Пополнить баланс' в главном меню и следуя инструкциям."
    },
    {
        "question": "Как проверить свой аккаунт?",
        "answer": "Перейдите в раздел 'Мой аккаунт', чтобы просмотреть информацию о вашем профиле."
    },
    # Вы можете добавить дополнительные FAQ пункты по необходимости
]

async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает список часто задаваемых вопросов.
    """
    keyboard = [
        [InlineKeyboardButton(item["question"], callback_data=f"faq_{index}")]
        for index, item in enumerate(FAQ_ITEMS)
    ]
    keyboard.append([InlineKeyboardButton("Отправить сообщение в поддержку", callback_data="send_support_message")])
    keyboard.append([InlineKeyboardButton("Назад", callback_data="go_back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text("❓ *Часто задаваемые вопросы:*", parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text("❓ *Часто задаваемые вопросы:*", parse_mode='Markdown', reply_markup=reply_markup)

    return SHOW_FAQ


async def show_faq_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает ответ на выбранный вопрос из FAQ.
    """
    query = update.callback_query
    await query.answer()

    # Извлекаем индекс вопроса из callback_data
    index = int(query.data.split("_")[-1])
    faq_item = FAQ_ITEMS[index]

    keyboard = [
        [InlineKeyboardButton("Другой вопрос", callback_data="show_faq")],
        [InlineKeyboardButton("Отправить сообщение в поддержку", callback_data="send_support_message")],
        [InlineKeyboardButton("Назад", callback_data="go_back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"**{faq_item['question']}**\n\n{faq_item['answer']}",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return SHOW_FAQ_ANSWER


async def initiate_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Инициализирует поддержку, сначала показывая FAQ.
    """
    await show_faq(update, context)
    return SHOW_FAQ


async def send_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает переход к отправке сообщения в поддержку.
    """
    await show_support_message_prompt(update, context)
    return SEND_SUPPORT_MESSAGE


async def show_support_message_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает пользователю приглашение отправить сообщение в поддержку.
    """
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="go_back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            "📝 *Отправьте ваше сообщение в поддержку:*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "📝 *Отправьте ваше сообщение в поддержку:*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )


async def start_support_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает сессию поддержки, показывая FAQ.
    """
    try:
        query = update.callback_query
        await query.answer()

        user = query.from_user
        telegram_id = user.id

        logger.debug(f"Начало сессии поддержки для telegram_id: {telegram_id}")

        api_url = f"{BACKEND_API_BASE_URL}/support/start-session/{telegram_id}/"

        response = requests.post(api_url)
        response.raise_for_status()
        data = response.json()
        session_id = data.get("session_id")

        if not session_id:
            logger.error("Не получен session_id от бэкенда.")
            await query.edit_message_text("❌ Произошла ошибка при начале сессии поддержки. Попробуйте позже.")
            return ConversationHandler.END

        context.user_data["support_session_id"] = session_id

        logger.debug(f"Сессия поддержки начата с session_id: {session_id}")

        # Инициализируем поддержку, показывая FAQ
        await show_faq(update, context)
        return SHOW_FAQ

    except requests.HTTPError as e:
        logger.error(f"HTTP ошибка при начале сессии поддержки: {e}")
        await update.callback_query.message.reply_text("❌ Произошла ошибка при начале сессии поддержки. Попробуйте позже.")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Неожиданная ошибка в start_support_session: {e}")
        await update.callback_query.message.reply_text("❌ Произошла непредвиденная ошибка. Попробуйте позже.")
        return ConversationHandler.END


# -------------------------------
# Функции для отправки сообщений поддержки
# -------------------------------

async def process_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает сообщение пользователя и отправляет его в бэкенд.
    """
    message_text = update.message.text.strip()
    session_id = context.user_data.get("support_session_id")
    user = update.message.from_user
    sender = (user.username or user.first_name)[:255]

    logger.debug(f"Отправка сообщения поддержки: session_id={session_id}, sender={sender}, message_text={message_text}")

    if not session_id:
        await update.message.reply_text("❌ Сессия поддержки не найдена. Пожалуйста, начните новую сессию.")
        return ConversationHandler.END

    api_url = f"{BACKEND_API_BASE_URL}/support/send-message/"
    data = {
        "session_id": session_id,
        "sender": sender,
        "message_text": message_text
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, json=data)
            response.raise_for_status()

            # Кнопка "Назад"
            keyboard = [
                [InlineKeyboardButton("Назад", callback_data="go_back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "✅ Сообщение успешно отправлено. Если у вас есть дополнительные вопросы, пожалуйста, продолжайте.",
                reply_markup=reply_markup
            )
            return SEND_SUPPORT_MESSAGE
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка при отправке сообщения поддержки: {e}")
            try:
                error_message = response.json().get('error', "❌ Произошла ошибка при отправке сообщения. Попробуйте позже.")
            except:
                error_message = "❌ Произошла ошибка при отправке сообщения. Попробуйте позже."
            await update.message.reply_text(f"{error_message}")
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке сообщения поддержки: {e}")
            await update.message.reply_text("❌ Произошла непредвиденная ошибка. Попробуйте позже.")
            return ConversationHandler.END

# -------------------------------
# Обработчики "Назад"
# -------------------------------

async def go_back_to_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает кнопку "Назад" для возврата к выбору плана подписки.
    """
    query = update.callback_query
    await query.answer()
    await show_subscription_plans(update, context)
    return SELECT_PLAN


async def go_back_to_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает кнопку "Назад" для возврата к выбору способов оплаты.
    """
    query = update.callback_query
    await query.answer()

    api_url = f"{BACKEND_API_BASE_URL}/payment-methods/"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        methods = response.json()

        keyboard = [
            [InlineKeyboardButton(method["name"], callback_data=f"select_method_{method['id']}")]
            for method in methods
        ]
        keyboard.append([InlineKeyboardButton("Назад", callback_data="go_back_to_plans")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "💳 Пожалуйста, выберите способ оплаты:", reply_markup=reply_markup
        )
        return SELECT_PAYMENT_METHOD
    except RequestException as e:
        logger.error(f"Ошибка при получении способов оплаты: {e}")
        await query.edit_message_text("❌ Произошла ошибка при получении способов оплаты. Попробуйте позже.")
        return ConversationHandler.END


async def go_back_to_gift_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает кнопку "Назад" для возврата к выбору плана подписки для подарка.
    """
    query = update.callback_query
    await query.answer()
    await select_gift_recipient(update, context)
    return SELECT_GIFT_PLAN


async def go_back_to_gift_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает кнопку "Назад" для возврата к выбору способов оплаты для подарка.
    """
    query = update.callback_query
    await query.answer()

    api_url = f"{BACKEND_API_BASE_URL}/payment-methods/"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        methods = response.json()

        keyboard = [
            [InlineKeyboardButton(method["name"], callback_data=f"select_gift_method_{method['id']}")]
            for method in methods
        ]
        keyboard.append([InlineKeyboardButton("Назад", callback_data="go_back_to_gift_plans")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "💳 Пожалуйста, выберите способ оплаты:", reply_markup=reply_markup
        )
        return SELECT_GIFT_PAYMENT_METHOD
    except RequestException as e:
        logger.error(f"Ошибка при получении способов оплаты: {e}")
        await query.edit_message_text("❌ Произошла ошибка при получении способов оплаты. Попробуйте позже.")
        return ConversationHandler.END

# -------------------------------
# Conversation Handler для подписки и поддержки
# -------------------------------

subscription_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(show_subscription_plans, pattern="^select_plan$"),
        CallbackQueryHandler(start_gifting_subscription, pattern="^gift_subscription$"),
        CallbackQueryHandler(start_support_session, pattern="^support$")
    ],
    states={
        # Состояния для подписки
        SELECT_PLAN: [
            CallbackQueryHandler(select_subscription_plan, pattern="^select_plan_\\d+$"),
            CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$"),
        ],
        SELECT_PAYMENT_METHOD: [
            CallbackQueryHandler(select_payment_method, pattern="^select_method_\\d+$"),
            CallbackQueryHandler(go_back_to_plans, pattern="^go_back_to_plans$"),
        ],
        ENTER_PAYMENT_DETAILS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_payment_details),
            CallbackQueryHandler(go_back_to_methods, pattern="^go_back_to_methods$"),
        ],
        # Состояния для подарка подписки
        SELECT_GIFT_RECIPIENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, select_gift_recipient),
        ],
        SELECT_GIFT_PLAN: [
            CallbackQueryHandler(select_gift_plan, pattern="^select_gift_plan_\\d+$"),
            CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$"),
        ],
        SELECT_GIFT_PAYMENT_METHOD: [
            CallbackQueryHandler(select_gift_payment_method, pattern="^select_gift_method_\\d+$"),
            CallbackQueryHandler(go_back_to_gift_plans, pattern="^go_back_to_gift_plans$"),
        ],
        ENTER_GIFT_PAYMENT_DETAILS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_gift_payment_details),
            CallbackQueryHandler(go_back_to_gift_methods, pattern="^go_back_to_gift_methods$"),
        ],
        # Состояния для поддержки
        SHOW_FAQ: [
            CallbackQueryHandler(show_faq, pattern="^show_faq$"),
            CallbackQueryHandler(show_faq_answer, pattern="^faq_\\d+$"),
            CallbackQueryHandler(send_support_message, pattern="^send_support_message$"),
            CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$")
        ],
        SHOW_FAQ_ANSWER: [
            CallbackQueryHandler(show_faq, pattern="^show_faq$"),
            CallbackQueryHandler(show_faq_answer, pattern="^faq_\\d+$"),
            CallbackQueryHandler(send_support_message, pattern="^send_support_message$"),
            CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$")
        ],
        SEND_SUPPORT_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_support_message),
            CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$")
        ],
    },
    fallbacks=[
        CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$"),
        CallbackQueryHandler(go_back_to_plans, pattern="^go_back_to_plans$"),
        CallbackQueryHandler(go_back_to_methods, pattern="^go_back_to_methods$"),
        CallbackQueryHandler(go_back_to_gift_plans, pattern="^go_back_to_gift_plans$"),
        CallbackQueryHandler(go_back_to_gift_methods, pattern="^go_back_to_gift_methods$"),
    ],
)
