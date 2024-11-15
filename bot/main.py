# main.py

import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)

# Import handlerlardan funksiyalar va ConversationHandlerlar
from start_handler import (
    start,
    register_user,
    check_agreements,
    handle_agreement_response,
    show_subscription_menu
)
from subscription_handler import subscription_conversation_handler
from client_card_handler import (
    client_card_conversation_handler,
    get_client_card_handler,
    show_main_menu
)
from other_handlers import (
    send_material,
    recharge_balance_conversation_handler,
    gift_subscription,
    my_account,
    feedback_conversation_handler,
    support_conversation_handler,
    go_back_to_menu
)

# Logging sozlash
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram bot tokenini o'zgartiring (bu yerda tokenni xavfsiz saqlash uchun .env faylidan foydalanishingiz tavsiya etiladi)
TOKEN = "7841284305:AAH3qeBWiTWXCwLmc2i9ulNGv_woLXO3WAo"

def main():
    # Application yaratish
    application = Application.builder().token(TOKEN).build()

    # ConversationHandler uchun holatlarni belgilang
    START, AGREEMENTS = range(2)

    # ConversationHandler uchun /start komandasi
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START: [CallbackQueryHandler(register_user, pattern="^register$")],
            AGREEMENTS: [
                CallbackQueryHandler(handle_agreement_response, pattern="^(accept_user_agreement|reject_user_agreement)$"),
                CallbackQueryHandler(show_subscription_menu, pattern="^show_subscription_menu$"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Handlerlarni qo'shish
    application.add_handler(conv_handler)
    application.add_handler(subscription_conversation_handler)
    application.add_handler(client_card_conversation_handler)
    application.add_handler(get_client_card_handler)

    # Boshqa CallbackQueryHandlerlar
    # application.add_handler(CallbackQueryHandler(start_session, pattern="^start_session$"))
    application.add_handler(CallbackQueryHandler(send_material, pattern="^materials$"))
    application.add_handler(recharge_balance_conversation_handler)
    application.add_handler(CallbackQueryHandler(gift_subscription, pattern="^gift_subscription$"))
    application.add_handler(CallbackQueryHandler(my_account, pattern="^my_account$"))
    application.add_handler(feedback_conversation_handler)
    application.add_handler(support_conversation_handler)
    application.add_handler(CallbackQueryHandler(go_back_to_menu, pattern="^go_back_to_menu$"))

    # Chatbots menu va individual chatbot handlerlari
    from other_handlers import chatbots_menu, chatbot_handlers
    application.add_handler(CallbackQueryHandler(chatbots_menu, pattern="^chatbots$"))
    for handler in chatbot_handlers:
        application.add_handler(handler)

    # Botni ishga tushurish
    application.run_polling()

if __name__ == "__main__":
    main()
