import html
import json
import logging
import traceback
from typing import List, Dict, Any
from warnings import filterwarnings

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler, filters, CallbackQueryHandler
)
from telegram.warnings import PTBUserWarning

from src.DndService import DndService
from src.class_submenus import class_submenus_query_handler, class_spells_menu_buttons_query_handler, \
    class_search_spells_text_handler, class_reading_spells_menu_buttons_query_handler, \
    class_spell_visualization_buttons_query_handler, class_resources_submenu_text_handler
from src.environment_variables_mg import keyring_initialize, keyring_get
from src.model.APIResource import APIResource
from src.model.AbilityScore import AbilityScore
from src.model.Alignment import Alignment
from src.model.ClassResource import ClassResource
from src.util import split_text_into_chunks, format_camel_case_to_title

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
MAIN_MENU, ITEM_DETAILS_MENU = map(chr, range(2))

# State definitions for class sub conversation
CLASS_SUBMENU, CLASS_SPELLS_SUBMENU, CLASS_RESOURCES_SUBMENU, CLASS_MANUAL_SPELLS_SEARCHING, CLASS_READING_SPELLS_SEARCHING, CLASS_SPELL_VISUALIZATION = map(
    chr, range(2, 8))

STOPPING = 99

# bot data keys
BOT_DATA_CHAT_IDS = 'bot_data_chat_ids'

# chat data keys
CURRENT_CLASS_SPELLS_INLINE_PAGE = 'current_class_spells_inline_page'

# callback keys
ABILITY_SCORE_CALLBACK = 'ability_score'
CLASS_SPELLS_PAGES = 'class_spells'
CLASS_SPELLS_PAGE = 'class_spells_page'

CLASSES = 'classes'
ABILITY_SCORES = 'ability-scores'
ALIGNMENTS = 'alignments'


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """
    The error callback function.
    This function is used to handle possible Telegram API errors that aren't handled.

    :param update: The Telegram update.
    :param context: The Telegram context.
    """
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Split the traceback into smaller parts
    tb_parts = [tb_string[i: i + 4096] for i in range(0, len(tb_string), 4096)]

    # Build the message with some markup and additional information about what happened.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    base_message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
    )

    # Send base message
    await context.bot.send_message(
        chat_id=keyring_get('DevId'), text=base_message, parse_mode=ParseMode.HTML
    )

    # Send each part of the traceback as a separate message
    for part in tb_parts:
        await context.bot.send_message(
            chat_id=keyring_get('DevId'), text=f"<pre>{html.escape(part)}</pre>", parse_mode=ParseMode.HTML
        )


async def post_stop_callback(application: Application) -> None:
    for chat_id in application.bot_data.get(BOT_DATA_CHAT_IDS, []):
        try:
            await application.bot.send_message(chat_id,
                                               "🔴 The bot was switched off... someone switched off the power 🔴")
        except (BadRequest, TelegramError) as e:
            logger.error(f"CHAT_ID: {chat_id} Telegram error stopping the bot: {e}")


def parse_resource(category: str, data: Dict[str, Any]) -> APIResource:
    # Add other categories and their respective parsing functions
    if category == ABILITY_SCORES:
        return AbilityScore(**data)
    elif category == CLASSES:
        return ClassResource(**data)
    elif category == ALIGNMENTS:
        return Alignment(**data)
    else:
        return APIResource(**data)


def process_keyboard_by_category(category: str, class_: APIResource) -> List:
    if category == CLASSES:
        return [
            [InlineKeyboardButton('Spell', callback_data=f"spells|{class_.spells}|{class_.name}")],
            [InlineKeyboardButton('Risorse di classe per livello',
                                  callback_data=f"resources|{class_.class_levels}|{class_.name}")]
        ]

    else:
        return []


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Add the chat_id to a list of IDs in order to allow the bot to contact them for communications reasons
    if BOT_DATA_CHAT_IDS in context.bot_data:
        context.bot_data[BOT_DATA_CHAT_IDS].add(update.effective_chat.id)
    else:
        context.bot_data[BOT_DATA_CHAT_IDS] = set()

    welcome_message: str = (f"Benvenuto player {update.effective_user.name}!\n"
                            f"Come posso aiutarti oggi?! Dispongo di tante funzioni... provale tutte!")

    main_resources: Dict[str, str] = {}

    try:
        async with DndService() as dnd_service:
            main_resources = await dnd_service.get_all_resources()
    except Exception as e:
        logger.error(f"Exception while getting main resources: {e}")
        await update.effective_message.reply_text(
            'Errore nel recuperare le risorse dalle API. Provare più tardi o un\'altra volta')
        return ConversationHandler.END

    # Create the keyboard
    keyboard = []
    row = []

    for resource_name, resource in main_resources.items():
        button = InlineKeyboardButton(format_camel_case_to_title(resource_name), callback_data=resource_name)
        row.append(button)

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    # send the keyboard
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(welcome_message, reply_markup=reply_markup)

    return MAIN_MENU


async def main_menu_buttons_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Manage inline buttons from main menu
    """
    query = update.callback_query
    category = query.data

    resources: List[APIResource] = []
    async with DndService() as dnd_service:
        resources = await dnd_service.get_available_resources(category)

    # Create the keyboard
    keyboard = []
    row = []

    for resource in resources:
        button = InlineKeyboardButton(resource.name, callback_data=f"{category}/{resource.index}")
        row.append(button)

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    # send the keyboard
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.answer()
    await query.edit_message_text(f"Seleziona un elemento in {category} o usa /stop per annullare il comando:",
                                  reply_markup=reply_markup)

    return ITEM_DETAILS_MENU


async def details_menu_buttons_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    path = query.data

    await query.answer()

    category, _ = path.split('/', 1)

    async with DndService() as dnd_service:
        resource_details = await dnd_service.get_resource_detail(path)

    resource = parse_resource(category, resource_details)
    details = str(resource)

    # process the keyboard based on the category
    keyboard = process_keyboard_by_category(category, resource)

    reply_markup = None
    if keyboard:
        reply_markup = InlineKeyboardMarkup(keyboard)

    if len(details) <= 4096:
        await query.edit_message_text(details, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else:
        await split_text_into_chunks(details, update, reply_markup=reply_markup)

    # choose the type of return based on the category selected. Returns END if there is no need to go deeper in the
    # conversation

    if category == CLASSES:
        return CLASS_SUBMENU
    else:
        return ConversationHandler.END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text('Ok! Use /start to start a new conversation!')
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

    class_options_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(class_submenus_query_handler, pattern=r"^(spells\|)|(resources\|)")],
        states={
            CLASS_SPELLS_SUBMENU: [CallbackQueryHandler(class_spells_menu_buttons_query_handler, pattern='^read-spells$|^search-spell$')],
            CLASS_MANUAL_SPELLS_SEARCHING: [MessageHandler(filters.TEXT & ~filters.COMMAND, class_search_spells_text_handler)],
            CLASS_READING_SPELLS_SEARCHING: [CallbackQueryHandler(class_reading_spells_menu_buttons_query_handler)],
            CLASS_SPELL_VISUALIZATION: [CallbackQueryHandler(class_spell_visualization_buttons_query_handler)],
            CLASS_RESOURCES_SUBMENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, class_resources_submenu_text_handler)]
        },
        fallbacks=[CommandHandler("stop", stop_nested)],
        map_to_parent={
            STOPPING: MAIN_MENU,
            ConversationHandler.END: MAIN_MENU
        }
    )

    main_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_handler)],
        states={
            MAIN_MENU: [CallbackQueryHandler(main_menu_buttons_query_handler, pattern='^[^/]+$'),
                        CommandHandler('start', start_handler)],
            ITEM_DETAILS_MENU: [CallbackQueryHandler(details_menu_buttons_query_handler, pattern='^.*/.*$')],
            CLASS_SUBMENU: [class_options_handler]
        },
        fallbacks=[CommandHandler("stop", stop)]
    )
    application.add_handler(main_handler)

    # Start the bot polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
