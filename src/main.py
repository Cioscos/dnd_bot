from typing import List
from warnings import filterwarnings
import logging

from telegram import Update, ReplyKeyboardMarkup, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, \
    ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    PicklePersistence, MessageHandler, filters, CallbackQueryHandler
)
from telegram.helpers import escape_markdown
from telegram.warnings import PTBUserWarning

from src.DndService import DndService
from src.TranslationService import TranslationService
from src.environment_variables_mg import keyring_initialize, keyring_get
from src.util import is_string_in_nested_lists, split_text_into_chunks

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%y-%m-%d %H:%M:%S',
    filename='password_bot.log'
)

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# State definitions for top-level conv handler
MAIN_MENU, PERSONAGGIO, CLASSE, RISORSE_DI_CLASSE, LIVELLI_DI_CLASSE = map(chr, range(5))
# State def for personaggio

# State def for punteggi abilità
PUNTEGGI_ABILITA = map(chr, range(1))

STOPPING = 99

MAIN_MENU_KEYBOARD: List[List[str]] = [['🧙‍♂ Personaggio 🧙‍♂', '🧮 Classe 🧮'],
                                       ['📖 Risorse di classe 📖', '📊 Livelli di classe 📊']]

# bot data keys
BOT_DATA_CHAT_IDS = 'bot_data_chat_ids'


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    The error callback function.
    This function is used to handle possible Telegram API errors that aren't handled.

    :param update: The Telegram update.
    :param context: The Telegram context.
    """
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error(f"Exception while handling an update: {context.error}")


async def post_stop_callback(application: Application) -> None:
    for chat_id in application.bot_data[BOT_DATA_CHAT_IDS]:
        try:
            await application.bot.send_message(chat_id,
                                               "🔴 The bot was switched off... someone switched off the power 🔴")
        except (BadRequest, TelegramError) as e:
            logger.error(f"CHAT_ID: {chat_id} Telegram error stopping the bot: {e}")


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Add the chat_id to a list of IDs in order to allow the bot to contact them for communications reasons
    if BOT_DATA_CHAT_IDS in context.bot_data:
        context.bot_data.append(update.effective_chat.id)
    else:
        context.bot_data[BOT_DATA_CHAT_IDS] = []

    welcome_message: str = (f"Benvenuto player {update.effective_user.name}!\n"
                            f"Come posso aiutarti oggi?! Dispongo di tante funzioni... provale tutte!")

    # send the keyboard
    reply_markup = ReplyKeyboardMarkup(
        MAIN_MENU_KEYBOARD,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder='Scegli cosa fare...'
    )

    await update.effective_message.reply_text(welcome_message, reply_markup=reply_markup)

    return MAIN_MENU


async def prepare_menu_for_personaggio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton('Punteggi abilità', callback_data='punteggi_abilità')],
        [InlineKeyboardButton('Allineamenti', callback_data='allineamenti')],
        [InlineKeyboardButton('Background', callback_data='background')],
        [InlineKeyboardButton('Linguaggi', callback_data='linguaggi')],
        [InlineKeyboardButton('Competenze', callback_data='competenze')],
        [InlineKeyboardButton('Abilità', callback_data='abilità')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text("Scegli una delle seguenti opzioni:", reply_markup=reply_markup)


async def handle_query_result_personaggio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    if data == 'punteggi_abilità':
        try:
            async with DndService() as service:
                data_ability_score = await service.get_ability_scores()
                results = data_ability_score['results']
                indexes = [result['index'] for result in results]

                msg_string = ''

                for index in indexes:
                    data = await service.get_ability_score(index)
                    msg_string += f"Abilità: *{data['full_name']}*\n"

                    desc = ' '.join(data['desc']) + '\n'
                    async with TranslationService() as translation:
                        desc = await translation.translate(desc)

                    msg_string += desc
                    names = [skill['name'] for skill in data['skills']]
                    msg_string += f"\nSkills: *{', '.join(names)}*\n\n"

                await split_text_into_chunks(msg_string, update)

        except Exception as e:
            logger.error(e)
            await update.effective_message.reply_text("Errore nel chiamare le API")

    await query.answer()
    return ConversationHandler.END


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text: str = update.message.text

    if is_string_in_nested_lists(text, MAIN_MENU_KEYBOARD):
        if text == '🧙‍♂ Personaggio 🧙‍♂':
            await prepare_menu_for_personaggio(update, context)
            return PERSONAGGIO

        elif text == '🧮 Classe 🧮':
            return CLASSE
        elif text == '📖 Risorse di classe 📖':
            return RISORSE_DI_CLASSE
        elif text == '📊 Livelli di classe 📊':
            return LIVELLI_DI_CLASSE


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END


async def stop_nested(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Comando stoppato")
    return STOPPING


def main() -> None:
    # Initialize the keyring
    if not keyring_initialize():
        exit(0xFF)

    application = (Application.builder()
                   .token(keyring_get('Telegram'))
                   .post_stop(post_stop_callback)).build()

    application.add_error_handler(error_handler)

    main_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_handler)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler)],
            PERSONAGGIO: [CallbackQueryHandler(handle_query_result_personaggio)],
        },
        fallbacks=[CommandHandler("stop", stop)]
    )
    application.add_handler(main_handler)

    # Start the bot polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
