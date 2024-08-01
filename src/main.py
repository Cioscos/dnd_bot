import html
import json
import logging
import traceback
from typing import List, Dict, Any, Union
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
from src.equipment_categories_submenus import equipment_categories_first_menu_query_handler, \
    equipment_visualization_query_handler
from src.graphql_queries import CATEGORY_TO_QUERY_MAP
from src.model import models
from src.model.APIResource import APIResource
from src.model.AbilityScore import AbilityScore
from src.model.Alignment import Alignment
from src.model.ClassResource import ClassResource
from src.model.Condition import Condition
from src.model.DamageType import DamageType
from src.model.Language import Language
from src.model.models import GraphQLBaseModel
from src.util import split_text_into_chunks, format_camel_case_to_title, generate_resource_list_keyboard, chunk_list, \
    async_graphql_query

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
MAIN_MENU, ITEM_DETAILS_MENU = map(chr, range(2))

# State definitions for class sub conversation
CLASS_SUBMENU, CLASS_SPELLS_SUBMENU, CLASS_RESOURCES_SUBMENU, CLASS_MANUAL_SPELLS_SEARCHING, CLASS_READING_SPELLS_SEARCHING, CLASS_SPELL_VISUALIZATION = map(
    chr, range(2, 8))

# state definitions for equipment-categories conversation
EQUIPMENT_CATEGORIES_SUBMENU, EQUIPMENT_VISUALIZATION = map(chr, range(8, 10))

# state definitions for features conversation
FEATURES_SUBMENU, FEATURE_VISUALIZATION = map(chr, range(10, 12))

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

# Excluded categories: These categories won't be shown in the first wiki menu
EXCLUDED_CATEGORIES = ['backgrounds', 'equipment', 'feats', 'features', 'magic-items', 'magic-schools', PROFICIENCIES]

# Not standard menù categories
NOT_STANDARD_MENU_CATEGORIES = [EQUIPMENT_CATEGORIES]

# graphql categories
GRAPHQL_ENDPOINT = 'https://www.dnd5eapi.co/graphql'
GRAPHQL_CATEOGRIES = [MONSTERS, PROFICIENCIES, RACES, RULE_SECTIONS, RULES, SKILLS]

# categories with HTML Parsing
HTML_PARSING_CATEGORIES = [MONSTERS, PROFICIENCIES, RACES, SKILLS]


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
    if CHARACTERS_CREATOR not in application.bot_data:
        application.bot_data[CHARACTERS_CREATOR] = {}


async def post_stop_callback(application: Application) -> None:
    for chat_id in application.bot_data.get(BOT_DATA_CHAT_IDS, []):
        try:
            await application.bot.send_message(chat_id,
                                               "🔴 The bot was switched off... someone switched off the power 🔴")
        except (BadRequest, TelegramError) as e:
            logger.error(f"CHAT_ID: {chat_id} Telegram error stopping the bot: {e}")


def parse_resource(category: str, data: Dict[str, Any], graphql_key: str = None) -> Union[
    APIResource, GraphQLBaseModel]:
    # Add other categories and their respective parsing functions
    if category == ABILITY_SCORES:
        return AbilityScore(**data)
    elif category == CLASSES:
        return ClassResource(**data)
    elif category == ALIGNMENTS:
        return Alignment(**data)
    elif category == CONDITIONS:
        return Condition(**data)
    elif category == DAMAGE_TYPES:
        return DamageType(**data)
    elif category == LANGUAGES:
        return Language(**data)
    elif category == MONSTERS:
        return models.Monster(**data[graphql_key])
    elif category == PROFICIENCIES:
        return models.Proficiency(**data[graphql_key])
    elif category == RACES:
        return models.Race(**data[graphql_key])
    elif category == RULE_SECTIONS:
        return models.RuleSection(**data[graphql_key])
    elif category == RULES:
        return models.Rule(**data[graphql_key])
    elif category == SKILLS:
        return models.Skill(**data[graphql_key])
    else:
        return APIResource(**data)


def process_keyboard_by_category(category: str, class_: Union[APIResource, GraphQLBaseModel]) -> List:
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

    context.chat_data[WIKI] = {}

    welcome_message: str = (f"Benvenuto player {update.effective_user.name}!\n"
                            f"Come posso aiutarti oggi?! Dispongo di tante funzioni... provale tutte!")

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
        if resource_name not in EXCLUDED_CATEGORIES:
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

    async with DndService() as dnd_service:
        resources = await dnd_service.get_available_resources(category)

    if len(resources) <= 100:

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

    else:
        # split the list into pages
        resource_pages = chunk_list(resources, 10)

        # save the inline pages in the context data
        context.chat_data[WIKI][INLINE_PAGES] = resource_pages

        if CURRENT_INLINE_PAGE_FOR_SUBMENUS not in context.chat_data[WIKI]:
            context.chat_data[WIKI][CURRENT_INLINE_PAGE_FOR_SUBMENUS] = 0

        # send the keyboard
        reply_markup = generate_resource_list_keyboard(
            resource_pages[context.chat_data[WIKI][CURRENT_INLINE_PAGE_FOR_SUBMENUS]])

    await query.answer()
    await query.edit_message_text(f"Seleziona un elemento in {category} o usa /stop per annullare il comando:",
                                  reply_markup=reply_markup)

    return ITEM_DETAILS_MENU


async def handle_pagination(query, context, direction):
    """Handle pagination of resource lists."""
    # initialize the CURRENT_INLINE_PAGE_FOR_SUBMENUS
    if CURRENT_INLINE_PAGE_FOR_SUBMENUS not in context.chat_data[WIKI]:
        context.chat_data[WIKI][CURRENT_INLINE_PAGE_FOR_SUBMENUS] = 0

    if direction == "prev_page":
        if context.chat_data[WIKI][CURRENT_INLINE_PAGE_FOR_SUBMENUS] == 0:
            await query.answer('Sei alla prima pagina!')
            return ITEM_DETAILS_MENU

        context.chat_data[WIKI][CURRENT_INLINE_PAGE_FOR_SUBMENUS] -= 1

    elif direction == "next_page":
        context.chat_data[WIKI][CURRENT_INLINE_PAGE_FOR_SUBMENUS] += 1

    try:
        resource_page = context.chat_data[WIKI][INLINE_PAGES][context.chat_data[WIKI][CURRENT_INLINE_PAGE_FOR_SUBMENUS]]
    except IndexError:
        await query.answer("Non ci sono altre pagine!")
        context.chat_data[WIKI][CURRENT_INLINE_PAGE_FOR_SUBMENUS] -= 1
        return ITEM_DETAILS_MENU

    reply_markup = generate_resource_list_keyboard(resource_page)
    await query.answer()
    await query.edit_message_text(f"(Premi /stop per tornare al menu principale)\n"
                                  f"Ecco la lista di equipaggiamenti:", reply_markup=reply_markup)
    return ITEM_DETAILS_MENU


async def handle_standard_category(query, update, category, path):
    """Handle standard categories."""
    async with DndService() as dnd_service:
        resource_details = await dnd_service.get_resource_detail(f"{category}/{path}")

    resource = parse_resource(category, resource_details)
    details = str(resource)

    keyboard = process_keyboard_by_category(category, resource)
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    await query.answer()

    if len(details) <= 4096:
        await query.edit_message_text(details, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else:
        await split_text_into_chunks(details, update, reply_markup=reply_markup)


async def handle_not_standard_category(query, context, resource_details):
    """Handle non-standard categories."""
    key_name = next(k for k, v in resource_details.items() if isinstance(v, list))

    resource_list = [APIResource(**result) for result in resource_details[key_name]]
    resource_pages = chunk_list(resource_list, 8)

    context.chat_data[WIKI][INLINE_PAGES] = resource_pages

    reply_markup = generate_resource_list_keyboard(resource_pages[0])

    await query.answer()
    await query.edit_message_text("Seleziona un elemento dalla lista o premi "
                                  "/stop per terminare la conversazione", reply_markup=reply_markup)


async def handle_graphql_category(query, update, category, data):
    """Handle GraphQL categories."""
    if data.startswith("/api"):
        variables = {'index': data.split('/')[3]}
    else:
        variables = {'index': data.split('/')[1]}
    resource_details = await async_graphql_query(GRAPHQL_ENDPOINT, CATEGORY_TO_QUERY_MAP[category], variables=variables)
    key = list(resource_details.keys())[0]
    resource = parse_resource(category, resource_details, key)
    details = str(resource)

    keyboard = process_keyboard_by_category(category, resource)
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    await query.answer()

    parse_mode = ParseMode.HTML if category in HTML_PARSING_CATEGORIES else ParseMode.MARKDOWN

    if len(details) <= 4096:
        if not hasattr(resource, 'image'):
            await query.edit_message_text(details, parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            await split_text_into_chunks(details, update, reply_markup=reply_markup, parse_mode=parse_mode,
                                         image=resource.image)
    else:
        await split_text_into_chunks(details, update, reply_markup=reply_markup, parse_mode=parse_mode)


async def details_menu_buttons_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    if data in ["prev_page", "next_page"]:
        return await handle_pagination(query, context, data)

    if not data.startswith("/api"):
        category, path = (data.split('/', 1) + [""])[:2]  # Safely split data into category and path

        if category in NOT_STANDARD_MENU_CATEGORIES:
            async with DndService() as dnd_service:
                resource_details = await dnd_service.get_resource_detail(f"{category}/{path}")
            await handle_not_standard_category(query, context, resource_details)
        elif category in GRAPHQL_CATEOGRIES:
            await handle_graphql_category(query, update, category, data)
        else:
            await handle_standard_category(query, update, category, path)

    else:
        category = data.split('/')[2]
        if category not in GRAPHQL_CATEOGRIES:
            async with DndService() as dnd_service:
                resource_details = await dnd_service.get_resource_by_class_resource(data)
            resource = parse_resource(category, resource_details)
        else:
            await handle_graphql_category(query, update, category, data)

        await query.answer()

        details = str(resource)
        keyboard = process_keyboard_by_category(category, resource)
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        if len(details) <= 4096:
            await query.edit_message_text(details, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        else:
            await split_text_into_chunks(details, update, reply_markup=reply_markup)

    if category == CLASSES:
        return CLASS_SUBMENU
    elif category == EQUIPMENT_CATEGORIES:
        return EQUIPMENT_CATEGORIES_SUBMENU
    else:
        return ConversationHandler.END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text('Ok! Use /start to start a new conversation!')
    context.chat_data[WIKI] = {}
    return ConversationHandler.END


async def stop_nested(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Comando stoppato")
    context.chat_data[WIKI] = {}
    return STOPPING


def main() -> None:
    # Initialize the keyring
    if not keyring_initialize():
        exit(0xFF)

    application = (Application.builder()
                   .token(keyring_get('Telegram'))
                   .post_init(post_init_callback)
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

    equipment_categories_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(equipment_categories_first_menu_query_handler)],
        states={
            EQUIPMENT_CATEGORIES_SUBMENU: [CallbackQueryHandler(equipment_categories_first_menu_query_handler)],
            EQUIPMENT_VISUALIZATION: [CallbackQueryHandler(equipment_visualization_query_handler)]
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
            ITEM_DETAILS_MENU: [CallbackQueryHandler(details_menu_buttons_query_handler)],
            CLASS_SUBMENU: [class_options_handler],
            EQUIPMENT_CATEGORIES_SUBMENU: [equipment_categories_handler]
        },
        fallbacks=[CommandHandler("stop", stop)]
    )
    application.add_handler(main_handler)

    # Start the bot polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
