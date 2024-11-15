# other_handlers.py

import logging
import httpx
from requests.exceptions import RequestException
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from functools import lru_cache

from client_card_handler import show_main_menu  # Faqat import qiling

logger = logging.getLogger(__name__)

# To'g'ri API bazasi URL'sini belgilang
BACKEND_API_BASE_URL = "http://localhost:8000/blog"  # Agar to'g'ri URL shu bo'lsa

# -------------------------------
# Konstanta Holatlarni Belgilash
# -------------------------------
RECHARGE_SELECT_PAYMENT_METHOD, RECHARGE_ENTER_AMOUNT, RECHARGE_ENTER_TRANSACTION_ID = range(3)
ENTER_FEEDBACK_STATE = 4
SUPPORT_DISPLAY_FAQ = 5
SEND_MATERIAL = 6

# -------------------------------
# Yordamchi Funksiyalar
# -------------------------------

def format_markdown_v2(text: str) -> str:
    """
    MarkdownV2 uchun maxsus belgilarni ekranirovka qiladi.
    """
    from telegram.helpers import escape_markdown  # Lokal import
    return escape_markdown(text, version=2)

def format_html_text(text: str) -> str:
    """
    HTML uchun maxsus belgilarni ekranirovka qiladi.
    """
    from html import escape  # Lokal import
    return escape(text)

# -------------------------------
# To'lov Usullarini Olish
# -------------------------------

@lru_cache(maxsize=1)
async def get_payment_methods():
    """
    Backenddan to'lov usullarini oladi va keshlaydi.
    """
    api_url = f"{BACKEND_API_BASE_URL}/payment-methods/"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url)
            response.raise_for_status()
            return response.json()
    except RequestException as e:
        logger.error(f"To'lov usullarini olishda xato: {e}")
        return []

# -------------------------------
# Asosiy Menyu va Boshqa Funksiyalar
# -------------------------------

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Asosiy menyuni ko'rsatadi.
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
        [InlineKeyboardButton("Чатботы", callback_data="chatbots")],
        [InlineKeyboardButton("Назад", callback_data="go_back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text("🏠 *Главное меню:*", parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text("🏠 *Главное меню:*", parse_mode='Markdown', reply_markup=reply_markup)

# -------------------------------
# Возврат в Главное Меню
# -------------------------------

async def go_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Foydalanuvchini asosiy menyuga qaytaradi.
    """
    query = update.callback_query
    await query.answer()
    await show_main_menu(update, context)
    return ConversationHandler.END

# -------------------------------
# Пополнение Баланса
# -------------------------------

async def start_recharge_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Balansni to'ldirish jarayonini boshlaydi.
    """
    query = update.callback_query
    await query.answer()

    # To'lov usullarini olish
    payment_methods = await get_payment_methods()
    logger.info(f"Available payment methods: {payment_methods}")

    if not payment_methods:
        logger.warning("No payment methods available.")
        await query.message.reply_text("В данный момент доступных способов оплаты нет.")
        await show_main_menu(update, context)
        return ConversationHandler.END

    # To'lov usullaridan tugmalar yaratish
    keyboard = [
        [InlineKeyboardButton(pm['name'], callback_data=f"payment_method_{pm['id']}")]
        for pm in payment_methods
    ]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="go_back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text("💳 Пожалуйста, выберите способ оплаты:", reply_markup=reply_markup)
    return RECHARGE_SELECT_PAYMENT_METHOD

async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    To'lov usulini tanlashni qayta ishlaydi.
    """
    query = update.callback_query
    await query.answer()
    payment_method_data = query.data

    logger.info(f"Selected payment method data: {payment_method_data}")

    if payment_method_data.startswith("payment_method_"):
        try:
            payment_method_id = int(payment_method_data.split("_")[-1])
            context.user_data['payment_method'] = payment_method_id
            logger.info(f"Selected payment method ID: {payment_method_id}")
            await query.message.reply_text("💳 Пожалуйста, введите сумму для пополнения:")
            return RECHARGE_ENTER_AMOUNT
        except ValueError:
            logger.error("Invalid payment method ID format.")
            await query.message.reply_text("❌ Некорректный выбор способа оплаты. Попробуйте снова.")
            return RECHARGE_SELECT_PAYMENT_METHOD
    elif payment_method_data == "go_back_to_menu":
        logger.info("User chose to go back to menu.")
        await show_main_menu(update, context)
        return ConversationHandler.END
    else:
        logger.error("Unexpected payment method selection.")
        await query.message.reply_text("❌ Некорректный выбор способа оплаты. Попробуйте снова.")
        return RECHARGE_SELECT_PAYMENT_METHOD

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Balansni to'ldirish summasini qabul qiladi.
    """
    amount_text = update.message.text
    logger.info(f"Entered amount: {amount_text}")
    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError("Summa musbat bo‘lishi kerak.")
        context.user_data['amount'] = amount
        await update.message.reply_text("✅ Пожалуйста, введите ID транзакции:")
        return RECHARGE_ENTER_TRANSACTION_ID
    except ValueError:
        logger.error("Invalid amount entered.")
        await update.message.reply_text("❌ Неверный формат суммы или сумма не положительная. Пожалуйста, введите число.")
        return RECHARGE_ENTER_AMOUNT

async def enter_transaction_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Balansni to'ldirish tranzaksiya ID sini qabul qiladi va API ga yuboradi.
    """
    transaction_id = update.message.text.strip()
    logger.info(f"Entered transaction ID: {transaction_id}")
    if not transaction_id:
        logger.error("Empty transaction ID entered.")
        await update.message.reply_text("❌ ID транзакции не может быть пустым. Пожалуйста, введите ID транзакции.")
        return RECHARGE_ENTER_TRANSACTION_ID

    user = update.message.from_user
    amount = context.user_data.get('amount')
    payment_method = context.user_data.get('payment_method')

    api_url = f"{BACKEND_API_BASE_URL}/make-payment/{user.id}/"
    data = {
        "payment_method": payment_method,
        "transaction_id": transaction_id,
        "amount": f"{amount:.2f}"
    }

    logger.debug(f"Sending POST request to {api_url} with data: {data}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=data)
            response.raise_for_status()
            await update.message.reply_text("✅ Баланс успешно пополнен!")
            logger.info("Balance successfully recharged.")
    except httpx.HTTPStatusError as e:
        logger.error(f"API error during balance recharge: {e}")
        try:
            error_message = response.json().get('error', "Произошла ошибка при пополнении баланса. Попробуйте позже.")
        except:
            error_message = "Произошла ошибка при пополнении баланса. Попробуйте позже."
        await update.message.reply_text(f"❌ {error_message}")
    except Exception as e:
        logger.error(f"Unexpected error during balance recharge: {e}")
        await update.message.reply_text("❌ Произошла непредвиденная ошибка при пополнении баланса. Попробуйте позже.")

    await show_main_menu(update, context)
    return ConversationHandler.END

# -------------------------------
# ConversationHandler for пополнение баланса
# -------------------------------
recharge_balance_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_recharge_balance, pattern="^recharge_balance$")],
    states={
        RECHARGE_SELECT_PAYMENT_METHOD: [
            CallbackQueryHandler(select_payment_method, pattern="^payment_method_\\d+$"),
            CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$")
        ],
        RECHARGE_ENTER_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)
        ],
        RECHARGE_ENTER_TRANSACTION_ID: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_transaction_id)
        ],
    },
    fallbacks=[
        CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$")
    ],
)

# -------------------------------
# Обратная Связь (Feedback)
# -------------------------------

async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начало процесса обратной связи.
    """
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("✉️ Пожалуйста, оставьте ваш отзыв:")
    return ENTER_FEEDBACK_STATE

async def enter_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка отправки отзыва.
    """
    feedback_text = update.message.text
    api_url = f"{BACKEND_API_BASE_URL}/feedback/"
    data = {"content": feedback_text}

    logger.info(f"Sending feedback data to API: {data}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=data)
            response.raise_for_status()
            await update.message.reply_text("✅ Спасибо за ваш отзыв!")
            logger.info("Feedback successfully sent.")
    except httpx.HTTPStatusError as e:
        logger.error(f"Error sending feedback: {e}")
        try:
            error_message = response.json().get('error', "Произошла ошибка при отправке отзыва. Попробуйте позже.")
        except:
            error_message = "Произошла ошибка при отправке отзыва. Попробуйте позже."
        await update.message.reply_text(f"❌ {error_message}")
    except Exception as e:
        logger.error(f"Unexpected error sending feedback: {e}")
        await update.message.reply_text("❌ Произошла непредвиденная ошибка при отправке отзыва. Попробуйте позже.")

    await show_main_menu(update, context)
    return ConversationHandler.END

feedback_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(feedback_start, pattern="^feedback$")],
    states={
        ENTER_FEEDBACK_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_feedback)],
    },
    fallbacks=[CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$")],
)

# -------------------------------
# Поддержка (Support) с FAQ
# -------------------------------

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

async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    'Поддержка' tugmasi bosilganda FAQ ni ko'rsatadi.
    """
    await support_faq(update, context)

async def support_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FAQ ro'yxatini ko'rsatadi.
    """
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton(item['question'], callback_data=f"faq_{idx+1}")]
        for idx, item in enumerate(FAQ_ITEMS)
    ]
    keyboard.append([InlineKeyboardButton("Чат поддержки", callback_data="start_support_chat")])
    keyboard.append([InlineKeyboardButton("Назад в главное меню", callback_data="go_back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    faq_message = "ℹ️ *Часто задаваемые вопросы (FAQ):*\n\n"
    for idx, item in enumerate(FAQ_ITEMS, start=1):
        faq_message += f"**{idx}. {item['question']}**\n\n"

    await query.message.edit_text(
        faq_message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return SUPPORT_DISPLAY_FAQ

async def handle_faq_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FAQ savoliga javob beradi.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("faq_"):
        try:
            faq_index = int(data.split("_")[1]) - 1
            if 0 <= faq_index < len(FAQ_ITEMS):
                selected_faq = FAQ_ITEMS[faq_index]
                answer_message = f"**{selected_faq['question']}**\n{selected_faq['answer']}"
                await query.message.reply_text(answer_message, parse_mode='Markdown')
                logger.info(f"Sent FAQ answer: {selected_faq['question']}")
            else:
                await query.message.reply_text("❌ Некорректный выбор вопроса.")
        except (IndexError, ValueError):
            await query.message.reply_text("❌ Некорректный выбор вопроса.")

        # Qo'shimcha tanlovlar
        keyboard = [
            [InlineKeyboardButton("Другие вопросы", callback_data="show_faq")],
            [InlineKeyboardButton("Чат поддержки", callback_data="start_support_chat")],
            [InlineKeyboardButton("Назад в главное меню", callback_data="go_back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Что бы вы хотели сделать дальше?", reply_markup=reply_markup)
        return SUPPORT_DISPLAY_FAQ

    elif data == "show_faq":
        await support_faq(update, context)
        return SUPPORT_DISPLAY_FAQ

    else:
        await query.message.reply_text("❌ Некорректный выбор.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Назад в главное меню", callback_data="go_back_to_menu")]
        ]))
        return SUPPORT_DISPLAY_FAQ

async def start_support_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает чат поддержки.
    """
    query = update.callback_query
    await query.answer()
    # Lokal import to avoid circular dependency
    from subscription_handler import start_support_session
    await start_support_session(update, context)

    await show_main_menu(update, context)
    return ConversationHandler.END

support_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(support_start, pattern="^support$")],
    states={
        SUPPORT_DISPLAY_FAQ: [
            CallbackQueryHandler(handle_faq_selection, pattern="^faq_\\d+$"),
            CallbackQueryHandler(start_support_chat, pattern="^start_support_chat$"),
            CallbackQueryHandler(support_faq, pattern="^show_faq$"),
            CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$")
        ],
    },
    fallbacks=[CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$")],
)

# -------------------------------
# Материалы
# -------------------------------

async def show_materials_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает меню "Материалы" с двумя кнопками: "Методичка" и "Рабочие тетради", а также "Назад".
    """
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Методичка", callback_data="material_methodichka")],
        [InlineKeyboardButton("Рабочие тетради", callback_data="material_workbooks")],
        [InlineKeyboardButton("Назад", callback_data="go_back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📚 *Материалы:*\nВыберите нужный раздел:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return SEND_MATERIAL

async def send_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отправляет выбранный материал пользователю.
    """
    query = update.callback_query
    await query.answer()

    data = query.data.split('_', 1)  # Faqat birinchi _ ni bo'lish
    logger.info(f"Received callback data: {query.data}")

    if len(data) != 2 or data[0] != 'material':
        logger.warning("Callback data format is incorrect.")
        await query.edit_message_text("❌ Некорректный выбор материала.")
        return ConversationHandler.END

    material_type = data[1]
    logger.info(f"Selected material type: {material_type}")

    # Backend API'dan hujjat URL sini olish
    try:
        async with httpx.AsyncClient() as client:
            api_url = f"{BACKEND_API_BASE_URL}/materials/"
            params = {'material_type': material_type}
            logger.info(f"Fetching materials with params: {params}")
            response = await client.get(api_url, params=params)
            response.raise_for_status()
            materials = response.json()
            logger.info(f"Received materials: {materials}")

            if not materials:
                logger.warning("No materials found for the selected type.")
                await query.edit_message_text("❌ Этот материал не доступен.")
                return ConversationHandler.END

            # Birinchi mavjud materialni tanlash
            material = materials[0]
            document_url = material.get('document_url')
            logger.info(f"Selected material: {material}")

            if not document_url:
                logger.warning("Document URL is missing in the selected material.")
                await query.edit_message_text("❌ Документ недоступен.")
                return ConversationHandler.END

            # Foydalanuvchiga hujjat yuborish
            if document_url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                await context.bot.send_photo(
                    chat_id=query.from_user.id,
                    photo=document_url,
                    caption=f"📄 *{material.get('title', 'Без названия')}*",
                    parse_mode='Markdown'
                )
                logger.info(f"Sent photo: {document_url}")
            else:
                await context.bot.send_document(
                    chat_id=query.from_user.id,
                    document=document_url,
                    caption=f"📄 *{material.get('title', 'Без названия')}*",
                    parse_mode='Markdown'
                )
                logger.info(f"Sent document: {document_url}")

            await show_main_menu(update, context)
            return ConversationHandler.END

    except httpx.HTTPStatusError as e:
        logger.error(f"API error while fetching material: {e.response.status_code} - {e.response.text}")
        await query.edit_message_text("❌ Ошибка при получении материала. Попробуйте позже.")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Unexpected error while sending material: {e}")
        await query.edit_message_text("❌ Произошла непредвиденная ошибка. Попробуйте позже.")
        return ConversationHandler.END


# -------------------------------
# Чатботы
# -------------------------------

async def chatbots_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает меню чатботов.
    """
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Карта клиента", callback_data="chatbot_karta_klienta")],
        [InlineKeyboardButton("Психотерапевт", callback_data="chatbot_psixoterapevt")],
        [InlineKeyboardButton("КПТ", callback_data="chatbot_kpt")],
        [InlineKeyboardButton("ЭТПР", callback_data="chatbot_etpr")],
        [InlineKeyboardButton("ТПО", callback_data="chatbot_tpo")],
        [InlineKeyboardButton("МКТ", callback_data="chatbot_mkt")],
        [InlineKeyboardButton("Асознание", callback_data="chatbot_asoznonost")],
        [InlineKeyboardButton("Управление тревожностью", callback_data="chatbot_upravleniya_trevozhnostyu")],
        [InlineKeyboardButton("Терапевтическое письмо", callback_data="chatbot_terapevticheskiy_pismo")],
        [InlineKeyboardButton("КФТ", callback_data="chatbot_kft")],
        [InlineKeyboardButton("ДПТ", callback_data="chatbot_dpt")],
        [InlineKeyboardButton("Схемотерапия", callback_data="chatbot_sxemoterapiya")],
        [InlineKeyboardButton("ИПТ", callback_data="chatbot_ipt")],
        [InlineKeyboardButton("Наративная терапия", callback_data="chatbot_narrativniya_terapiya")],
        [InlineKeyboardButton("Назад", callback_data="go_back_to_menu")]  # "Назад" tugmasi
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text("Выберите чатбот:", reply_markup=reply_markup)
    return ConversationHandler.END

# Individual chatbot handlerlari
async def chatbot_karta_klienta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-AAZLzsVUt-karta-"
    await update.callback_query.message.reply_text(f"Карта клиента: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def chatbot_psixoterapevt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-eyMvqlNiM-psikhoterapevt"
    await update.callback_query.message.reply_text(f"Психотерапевт: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def chatbot_kpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-cZG535IXC-final-kpt-klaud"
    await update.callback_query.message.reply_text(f"КПТ: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def chatbot_etpr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-0JYTCDgTg-2ekspozitsionnaia-terapiia-s-predotvrashchen-etpr-erp"
    await update.callback_query.message.reply_text(f"ЭТПР: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def chatbot_tpo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-VwRfjHabS-iact-2"
    await update.callback_query.message.reply_text(f"ТПО: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def chatbot_mkt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-v10DeVqh6-metakognitivnaia-terapiia-mkt"
    await update.callback_query.message.reply_text(f"МКТ: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def chatbot_asoznonost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-ugnxXY2jQ-2-midlness"
    await update.callback_query.message.reply_text(f"Асознание: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def chatbot_upravleniya_trevozhnostyu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-WVMzU9zuB-2-upravlenie-trevozhnostyu"
    await update.callback_query.message.reply_text(f"Управление тревожностью: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def chatbot_terapevticheskiy_pismo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-Dw5eNVKOe-2-terapevticheskoe-pismo"
    await update.callback_query.message.reply_text(f"Терапевтическое письмо: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def chatbot_kft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-Sc8zMP0vZ-2-kratkosrochnaia"
    await update.callback_query.message.reply_text(f"КФТ: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def chatbot_dpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-DwyXSdVET-2dpt"
    await update.callback_query.message.reply_text(f"ДПТ: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def chatbot_sxemoterapiya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-OP639c1bE-2skhemoterapiya"
    await update.callback_query.message.reply_text(f"Схемотерапия: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def chatbot_ipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-qUGJ1Zfr0-2-interpersonalnaia"
    await update.callback_query.message.reply_text(f"ИПТ: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def chatbot_narrativniya_terapiya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    link = "https://chatgpt.com/g/g-VtOyysCkq-2-narrativnaia"
    await update.callback_query.message.reply_text(f"Наративная терапия: {link}")
    await show_main_menu(update, context)
    return ConversationHandler.END

# Chatbotlar uchun handlerlar ro'yxati
chatbot_handlers = [
    CallbackQueryHandler(chatbot_karta_klienta, pattern="^chatbot_karta_klienta$"),
    CallbackQueryHandler(chatbot_psixoterapevt, pattern="^chatbot_psixoterapevt$"),
    CallbackQueryHandler(chatbot_kpt, pattern="^chatbot_kpt$"),
    CallbackQueryHandler(chatbot_etpr, pattern="^chatbot_etpr$"),
    CallbackQueryHandler(chatbot_tpo, pattern="^chatbot_tpo$"),
    CallbackQueryHandler(chatbot_mkt, pattern="^chatbot_mkt$"),
    CallbackQueryHandler(chatbot_asoznonost, pattern="^chatbot_asoznonost$"),
    CallbackQueryHandler(chatbot_upravleniya_trevozhnostyu, pattern="^chatbot_upravleniya_trevozhnostyu$"),
    CallbackQueryHandler(chatbot_terapevticheskiy_pismo, pattern="^chatbot_terapevticheskiy_pismo$"),
    CallbackQueryHandler(chatbot_kft, pattern="^chatbot_kft$"),
    CallbackQueryHandler(chatbot_dpt, pattern="^chatbot_dpt$"),
    CallbackQueryHandler(chatbot_sxemoterapiya, pattern="^chatbot_sxemoterapiya$"),
    CallbackQueryHandler(chatbot_ipt, pattern="^chatbot_ipt$"),
    CallbackQueryHandler(chatbot_narrativniya_terapiya, pattern="^chatbot_narrativniya_terapiya$")
]

# -------------------------------
# Мой Аккаунт (My Account)
# -------------------------------

async def my_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает информацию о аккаунте пользователя.
    """
    query = update.callback_query
    await query.answer()
    user = query.from_user
    api_url = f"{BACKEND_API_BASE_URL}/profile/{user.id}/"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url)
            response.raise_for_status()
            user_data = response.json()

            # Экранирование пользовательских данных для HTML
            username = format_html_text(user_data.get('username', 'Неизвестно'))
            created = format_html_text(user_data.get('created', 'Неизвестно'))

            message = f"👤 <b>Ваш аккаунт:</b>\n"
            message += f"Имя пользователя: <b>{username}</b>\n"
            message += f"Дата регистрации: <b>{created}</b>\n"

            current_subscription = user_data.get('current_subscription')
            if current_subscription and isinstance(current_subscription, dict):
                plan = current_subscription.get('plan')
                if isinstance(plan, dict):
                    plan_name = format_html_text(plan.get('name', 'Неизвестно'))
                else:
                    plan_name = 'Неизвестно'

                end_date = format_html_text(current_subscription.get('end_date', 'Неизвестно'))

                message += f"Текущая подписка: <b>{plan_name}</b>\n"
                message += f"Подписка действует до: <b>{end_date}</b>\n"
            else:
                message += "<b>Текущая подписка:</b> Отсутствует\n"

            total_payments = user_data.get('total_payments', 0)
            balance = user_data.get('balance', 0)

            message += f"<b>Всего платежей:</b> {total_payments}\n"
            message += f"<b>Баланс:</b> {balance} сум\n"

            await query.message.reply_text(message, parse_mode='HTML')
            logger.info("Sent account information to user.")
    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка при получении информации об аккаунте: {e}")
        await query.message.reply_text("❌ Произошла ошибка при получении информации об аккаунте. Попробуйте позже.")
    except (KeyError, TypeError) as e:
        logger.error(f"Ошибка обработки данных профиля: {e}")
        await query.message.reply_text("❌ Произошла ошибка при обработке информации об аккаунте. Попробуйте позже.")

    await show_main_menu(update, context)
    return ConversationHandler.END

# -------------------------------
# Подарить Подписку (Gift Subscription)
# -------------------------------

async def gift_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Foydalanuvchini gift subscription handleriga yuboradi.
    """
    # Lokal import to avoid circular dependency
    from subscription_handler import start_gifting_subscription
    await start_gifting_subscription(update, context)

# -------------------------------
# Handlerlarni Qo‘shish
# -------------------------------

def add_other_handlers(application):
    """
    Barcha handlerlarni Telegram botga qo'shadi.
    """
    # Пополнение баланса ConversationHandler
    application.add_handler(recharge_balance_conversation_handler)

    # Обратная связь ConversationHandler
    application.add_handler(feedback_conversation_handler)

    # Материалы ConversationHandler
    application.add_handler(materials_conversation_handler)

    # Поддержка ConversationHandler
    application.add_handler(support_conversation_handler)

    # Чатботы ConversationHandler
    application.add_handler(CallbackQueryHandler(chatbots_menu, pattern="^chatbots$"))

    # Individual chatbot handlerlari
    for handler in chatbot_handlers:
        application.add_handler(handler)

    # Подарить подписку handler
    application.add_handler(CallbackQueryHandler(gift_subscription, pattern="^gift_subscription$"))

    # Мой аккаунт handler
    application.add_handler(CallbackQueryHandler(my_account, pattern="^my_account$"))

    # Возврат в главное меню handler
    application.add_handler(CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$"))
