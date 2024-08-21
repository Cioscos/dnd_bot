import html
import json
import logging
import traceback
from warnings import filterwarnings

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler, filters, CallbackQueryHandler, PicklePersistence
)
from telegram.warnings import PTBUserWarning

from character_creator import character_creator_start_handler, character_creation_handler, \
    character_spells_query_handler, character_abilities_query_handler, character_feature_point_query_handler, \
    character_name_handler, character_race_handler, character_gender_handler, character_class_handler, \
    character_subclass_query_handler, character_multiclassing_query_handler, character_creator_stop_nested
from class_submenus import class_submenus_query_handler, class_spells_menu_buttons_query_handler, \
    class_search_spells_text_handler, class_reading_spells_menu_buttons_query_handler, \
    class_spell_visualization_buttons_query_handler, class_resources_submenu_text_handler
from environment_variables_mg import keyring_initialize, keyring_get
from equipment_categories_submenus import equipment_categories_first_menu_query_handler, \
    equipment_visualization_query_handler
from src.character_creator import character_bag_query_handler, character_selection_query_handler
from wiki import wiki_main_menu_handler, main_menu_buttons_query_handler, details_menu_buttons_query_handler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%y-%m-%d %H:%M:%S',
    filename='dnd_beyond.log',
    filemode='w'
)

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# State definitions for top-level conv handler
START_MENU, WIKI_MENU, CHARACTERS_CREATOR_MENU, ITEM_DETAILS_MENU = map(int, range(4))

# State definitions for class sub conversation
CLASS_SUBMENU, CLASS_SPELLS_SUBMENU, CLASS_RESOURCES_SUBMENU, CLASS_MANUAL_SPELLS_SEARCHING, CLASS_READING_SPELLS_SEARCHING, CLASS_SPELL_VISUALIZATION = map(
    int, range(4, 10))

# state definitions for equipment-categories conversation
EQUIPMENT_CATEGORIES_SUBMENU, EQUIPMENT_VISUALIZATION = map(int, range(10, 12))

# state definitions for features conversation
FEATURES_SUBMENU, FEATURE_VISUALIZATION = map(int, range(12, 14))

# states definition for character creator submenu
(CHARACTER_CREATION, CHARACTER_SELECTION, NAME_SELECTION, RACE_SELECTION, GENDER_SELECTION,
 CLASS_SELECTION, FUNCTION_SELECTION) = map(int, range(14, 21))

STOPPING = 99

# bot data keys
BOT_DATA_CHAT_IDS = 'bot_data_chat_ids'

# chat data keys
WIKI = 'wiki'
CHARACTERS_CREATOR = 'characters_creator'
CURRENT_INLINE_PAGE_FOR_SUBMENUS = 'current_inline_page_for_submenu'
INLINE_PAGES = 'inline_pages'

# callback keys
ABILITY_SCORE_CALLBACK = 'ability_score'
CLASS_SPELLS_PAGES = 'class_spells'
CLASS_SPELLS_PAGE = 'class_spells_page'

# character creator callback keys
BAG_CALLBACK_DATA = 'bag'
SPELLS_CALLBACK_DATA = 'spells'
ABILITIES_CALLBACK_DATA = 'abilities'
FEATURE_POINTS_CALLBACK_DATA = 'feature_points'
SUBCLASS_CALLBACK_DATA = 'subclass'
MULTICLASSING_CALLBACK_DATA = 'multiclass'

# Categories
CLASSES = 'classes'
ABILITY_SCORES = 'ability-scores'
ALIGNMENTS = 'alignments'
CONDITIONS = 'conditions'
DAMAGE_TYPES = 'damage-types'
EQUIPMENT_CATEGORIES = 'equipment-categories'
EQUIPMENT = 'equipment'
LANGUAGES = 'languages'
MONSTERS = 'monsters'
PROFICIENCIES = 'proficiencies'
RACES = 'races'
RULE_SECTIONS = 'rule-sections'
RULES = 'rules'
SKILLS = 'skills'
SPELLS = 'spells'
SUBCLASSES = 'subclasses'
SUBRACES = 'subraces'
TRAITS = 'traits'
WEAPON_PROPERTIES = 'weapon-properties'

# Excluded categories: These categories won't be shown in the first wiki menu
EXCLUDED_CATEGORIES = ['backgrounds',
                       'equipment',
                       'feats',
                       'features',
                       'magic-items',
                       'magic-schools',
                       PROFICIENCIES,
                       SUBCLASSES,
                       SUBRACES,
                       TRAITS]

# Not standard menù categories
NOT_STANDARD_MENU_CATEGORIES = [EQUIPMENT_CATEGORIES]

# graphql categories
GRAPHQL_ENDPOINT = 'https://www.dnd5eapi.co/graphql'
GRAPHQL_CATEOGRIES = [MONSTERS, PROFICIENCIES, RACES, RULE_SECTIONS, RULES, SKILLS, SPELLS, WEAPON_PROPERTIES]

# categories with HTML Parsing
HTML_PARSING_CATEGORIES = [MONSTERS, PROFICIENCIES, RACES, SKILLS, SPELLS, WEAPON_PROPERTIES]


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


async def post_init_callback(application: Application) -> None:
    for chat_id in application.bot_data.get(BOT_DATA_CHAT_IDS, []):
        try:
            await application.bot.send_message(chat_id,
                                               "🟢 Il Bot è ripartito dopo un riavvio 🟢")
        except (BadRequest, TelegramError) as e:
            logger.error(f"CHAT_ID: {chat_id} Telegram error stopping the bot: {e}")


async def post_stop_callback(application: Application) -> None:
    for chat_id in application.bot_data.get(BOT_DATA_CHAT_IDS, []):
        try:
            await application.bot.send_message(chat_id,
                                               "🔴 Il bot si è spento... qualcuno è a lavoro o è scattato il contatore! 🔴")
        except (BadRequest, TelegramError) as e:
            logger.error(f"CHAT_ID: {chat_id} Telegram error stopping the bot: {e}")


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Add the chat_id to a list of IDs in order to allow the bot to contact them for communications reasons
    if BOT_DATA_CHAT_IDS in context.bot_data:
        context.bot_data[BOT_DATA_CHAT_IDS].add(update.effective_chat.id)
    else:
        context.bot_data[BOT_DATA_CHAT_IDS] = set()
        context.bot_data[BOT_DATA_CHAT_IDS].add(update.effective_chat.id)

    # initialize WIKI section in chat_data
    context.chat_data[WIKI] = {}

    welcome_message: str = (f"Benvenuto player {update.effective_user.name}!\n"
                            f"Come posso aiutarti oggi?! Dispongo di una sezione Wiki che ti permetterà di consultare "
                            f"comodamente granparte del manuale D&D 5e!\n"
                            f"La sezione creazione del personaggio invece permette la gestione di un personaggio, del "
                            f"suo inventario e delle sue spell.")

    keyboard = [
        [InlineKeyboardButton('Wiki', callback_data="wiki"),
         InlineKeyboardButton('Gestione personaggio', callback_data="character_manager")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

    return START_MENU


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text('Ok! Usa il comando /start per avviare una nuova conversazione!\n'
                                              'Oppure invia direttamente i comandi /wiki o /character')
    context.chat_data[WIKI] = {}
    return ConversationHandler.END


async def stop_nested(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Ok! Usa i comandi:\n"
                                    "/wiki per consultare la wiki\n"
                                    "/character per usare il gestore di personaggi")
    context.chat_data[WIKI] = {}
    return STOPPING


def main() -> None:
    # Initialize the keyring
    if not keyring_initialize():
        exit(0xFF)

    # Initialize the Pickle database
    persistence = PicklePersistence(filepath='DB.pkl')

    application = (Application.builder()
                   .token(keyring_get('Telegram'))
                   .post_init(post_init_callback)
                   .post_stop(post_stop_callback)
                   .persistence(persistence)).build()

    application.add_error_handler(error_handler)

    class_options_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(class_submenus_query_handler, pattern=r"^(spells\|)|(resources\|)")],
        states={
            CLASS_SPELLS_SUBMENU: [
                CallbackQueryHandler(class_spells_menu_buttons_query_handler, pattern='^(read-spells|search-spell)$')],
            CLASS_MANUAL_SPELLS_SEARCHING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, class_search_spells_text_handler)],
            CLASS_READING_SPELLS_SEARCHING: [CallbackQueryHandler(class_reading_spells_menu_buttons_query_handler)],
            CLASS_SPELL_VISUALIZATION: [CallbackQueryHandler(class_spell_visualization_buttons_query_handler)],
            CLASS_RESOURCES_SUBMENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, class_resources_submenu_text_handler)]
        },
        fallbacks=[CommandHandler("stop", stop_nested)],
        map_to_parent={
            STOPPING: ConversationHandler.END,
            ConversationHandler.END: ConversationHandler.END,
            CLASS_SUBMENU: CLASS_SUBMENU
        },
        name='class_options_handler_v1',
        persistent=True
    )

    equipment_categories_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(equipment_categories_first_menu_query_handler)],
        states={
            EQUIPMENT_CATEGORIES_SUBMENU: [CallbackQueryHandler(equipment_categories_first_menu_query_handler)],
            EQUIPMENT_VISUALIZATION: [CallbackQueryHandler(equipment_visualization_query_handler)]
        },
        fallbacks=[CommandHandler("stop", stop_nested)],
        map_to_parent={
            STOPPING: ConversationHandler.END,
            ConversationHandler.END: ConversationHandler.END
        },
        name='equipment_categories_handler_v1',
        persistent=True
    )

    wiki_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(wiki_main_menu_handler, pattern=r"^wiki$"),
            CommandHandler('wiki', wiki_main_menu_handler)
        ],
        states={
            WIKI_MENU: [CallbackQueryHandler(main_menu_buttons_query_handler, pattern='^[^/]+$'),
                        CommandHandler('wiki', wiki_main_menu_handler)],
            ITEM_DETAILS_MENU: [CallbackQueryHandler(details_menu_buttons_query_handler)],
            CLASS_SUBMENU: [class_options_handler],
            EQUIPMENT_CATEGORIES_SUBMENU: [equipment_categories_handler]
        },
        fallbacks=[CommandHandler("stop", stop_nested)],
        map_to_parent={
            STOPPING: ConversationHandler.END,
            ConversationHandler.END: ConversationHandler.END
        },
        name='wiki_handler_v1',
        persistent=True
    )

    character_creator_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(character_creator_start_handler, pattern=r"^character_manager$"),
            CommandHandler('character', character_creator_start_handler)
        ],
        states={
            CHARACTER_CREATION: [CommandHandler('newCharacter', character_creation_handler)],
            NAME_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, character_name_handler)],
            RACE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, character_race_handler)],
            GENDER_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, character_gender_handler)],
            CLASS_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, character_class_handler)],
            FUNCTION_SELECTION: [
                CallbackQueryHandler(character_bag_query_handler, pattern=fr"^{BAG_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_spells_query_handler, pattern=fr"^{SPELLS_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_abilities_query_handler, pattern=fr"^{ABILITIES_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_feature_point_query_handler,
                                     pattern=fr"^{FEATURE_POINTS_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_subclass_query_handler,
                                     pattern=fr"^{SUBCLASS_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_multiclassing_query_handler,
                                     pattern=fr"^{MULTICLASSING_CALLBACK_DATA}$")
            ],
            CHARACTER_SELECTION: [
                CallbackQueryHandler(character_selection_query_handler),
                CommandHandler('newCharacter', character_creation_handler)
            ]
        },
        fallbacks=[CommandHandler("stop", character_creator_stop_nested)],
        map_to_parent={
            STOPPING: ConversationHandler.END,
            ConversationHandler.END: ConversationHandler.END
        },
        name='character_creator_handler_v1',
        persistent=True
    )

    main_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start_handler),
            wiki_handler,
            character_creator_handler
        ],
        states={
            START_MENU: [wiki_handler, character_creator_handler]
        },
        fallbacks=[CommandHandler("stop", stop)],
        name='main_handler_v1',
        persistent=True
    )
    application.add_handler(main_handler)

    # Start the bot polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
