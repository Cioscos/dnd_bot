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
    character_multiclassing_query_handler, \
    BAG_CALLBACK_DATA, SPELLS_CALLBACK_DATA, ABILITIES_CALLBACK_DATA, FEATURE_POINTS_CALLBACK_DATA, \
    MULTICLASSING_CALLBACK_DATA, character_deleting_query_handler, \
    DELETE_CHARACTER_CALLBACK_DATA, CHARACTER_DELETION, character_deleting_answer_query_handler, \
    character_bag_new_object_query_handler, BAG_ITEM_INSERTION, character_bag_item_insert, character_hit_points_handler, \
    BAG_ITEM_INSERTION_CALLBACK_DATA, BAG_ITEM_EDIT, character_bag_edit_object_query_handler, \
    character_bag_item_delete_one_handler, character_bag_item_add_one_handler, character_bag_item_delete_all_handler, \
    BAG_ITEM_EDIT_CALLBACK_DATA, FEATURE_POINTS_EDIT, character_feature_points_edit_query_handler, CHARACTER_CREATION, \
    NAME_SELECTION, RACE_SELECTION, GENDER_SELECTION, CLASS_SELECTION, FUNCTION_SELECTION, CHARACTER_SELECTION, \
    character_creator_stop_submenu, character_bag_item_edit_handler, ABILITIES_MENU, \
    character_abilities_menu_query_handler, \
    character_ability_visualization_query_handler, ABILITY_ACTIONS, character_ability_edit_handler, \
    character_ability_delete_query_handler, character_ability_text_handler, character_ability_new_query_handler, \
    character_change_level_query_handler, character_spells_menu_query_handler, \
    character_spell_visualization_query_handler, character_spell_new_query_handler, character_spell_learn_handler, \
    character_spell_edit_handler, character_spell_delete_query_handler, character_multiclassing_add_class_query_handler, \
    MULTICLASSING_ADD_CALLBACK_DATA, character_multiclassing_add_class_answer_handler, \
    character_multiclassing_remove_class_query_handler, character_multiclassing_remove_class_answer_query_handler, \
    character_level_change_class_choice_handler, LEVEL_UP_CALLBACK_DATA, LEVEL_DOWN_CALLBACK_DATA, \
    SPELLS_SLOT_CALLBACK_DATA, character_multiclassing_reassign_levels_query_handler, SPELLS_SLOTS_MANAGEMENT, \
    character_spells_slots_mode_answer_query_handler, character_spells_slots_add_query_handler, \
    SPELLS_SLOTS_INSERT_CALLBACK_DATA, character_spell_slot_add_answer_query_handler, \
    character_spells_slots_query_handler, SPELLS_SLOTS_REMOVE_CALLBACK_DATA, \
    character_spells_slots_remove_query_handler, character_spell_slot_remove_answer_query_handler, \
    character_spells_slot_use_slot_query_handler, SPELL_SLOT_SELECTED_CALLBACK_DATA, \
    character_spells_slot_use_reset_query_handler, SPELLS_SLOTS_RESET_CALLBACK_DATA, \
    character_spells_slot_change_mode_query_handler, SPELLS_SLOTS_CHANGE_CALLBACK_DATA, DAMAGE_CALLBACK_DATA, \
    HEALING_CALLBACK_DATA, character_damage_query_handler, character_healing_query_handler, \
    character_hit_points_query_handler, HIT_POINTS_CALLBACK_DATA, \
    character_hit_points_registration_handler, character_damage_registration_handler, LONG_REST_WARNING_CALLBACK_DATA, \
    character_long_rest_warning_query_handler, LONG_REST_CALLBACK_DATA, character_long_rest_query_handler, \
    ROLL_DICE_MENU_CALLBACK_DATA, dice_handler, dice_actions_query_handler, character_ability_features_query_handler, \
    character_ability_insert_query_handler, SPELL_LEARN_CALLBACK_DATA, character_short_rest_warning_query_handler, \
    character_creation_stop, OVER_HEALING_CONFIRMATION, character_healing_value_check_or_registration_handler, \
    character_over_healing_registration_query_handler, character_generic_main_menu_query_handler, \
    ROLL_DICE_CALLBACK_DATA, ROLL_DICE_DELETE_HISTORY_CALLBACK_DATA, SPELL_EDIT_CALLBACK_DATA, \
    SPELL_DELETE_CALLBACK_DATA, SPELL_BACK_MENU_CALLBACK_DATA, ABILITY_EDIT_CALLBACK_DATA, ABILITY_ACTIVE_CALLBACK_DATA, \
    ABILITY_DELETE_CALLBACK_DATA, ABILITY_USE_CALLBACK_DATA, ABILITY_BACK_MENU_CALLBACK_DATA, \
    ABILITY_LEARN_CALLBACK_DATA, AFFERMATIVE_CHARACTER_DELETION_CALLBACK_DATA, \
    NEGATIVE_CHARACTER_DELETION_CALLBACK_DATA, SPELL_USE_CALLBACK_DATA, character_spell_use_query_handler, \
    SPELL_USAGE_BACK_MENU_CALLBACK_DATA, character_bag_ask_item_overwrite_quantity_query_handler, BAG_ITEM_OVERWRITE, \
    character_ask_item_overwrite_quantity, SETTINGS_CALLBACK_DATA, character_creator_settings, SETTINGS_MENU_STATE, \
    character_creator_settings_callback_handler
from class_submenus import class_submenus_query_handler, class_spells_menu_buttons_query_handler, \
    class_search_spells_text_handler, class_reading_spells_menu_buttons_query_handler, \
    class_spell_visualization_buttons_query_handler, class_resources_submenu_text_handler, CLASS_SPELLS_SUBMENU, \
    CLASS_MANUAL_SPELLS_SEARCHING, CLASS_READING_SPELLS_SEARCHING, CLASS_SPELL_VISUALIZATION, CLASS_RESOURCES_SUBMENU, \
    CLASS_SUBMENU
from environment_variables_mg import keyring_initialize, keyring_get
from equipment_categories_submenus import equipment_categories_first_menu_query_handler, \
    equipment_visualization_query_handler, EQUIPMENT_CATEGORIES_SUBMENU, EQUIPMENT_VISUALIZATION
from src.character_creator import character_bag_query_handler, character_selection_query_handler, BAG_MANAGEMENT, \
    HIT_POINTS_SELECTION, ABILITY_VISUALIZATION, ABILITY_LEARN, SPELLS_MENU, SPELL_VISUALIZATION, SPELL_ACTIONS, \
    SPELL_LEARN, MULTICLASSING_ACTIONS, MULTICLASSING_REMOVE_CALLBACK_DATA, SPELL_SLOT_ADDING, SPELL_SLOT_REMOVING, \
    DAMAGE_REGISTRATION, HEALING_REGISTRATION, HIT_POINTS_REGISTRATION, LONG_REST, DICE_ACTION, \
    ABILITY_IS_PASSIVE_CALLBACK_DATA, ABILITY_RESTORATION_TYPE_CALLBACK_DATA, ABILITY_INSERT_CALLBACK_DATA, SHORT_REST, \
    character_short_rest_query_handler, SHORT_REST_CALLBACK_DATA, SHORT_REST_WARNING_CALLBACK_DATA
from wiki import wiki_main_menu_handler, main_menu_buttons_query_handler, details_menu_buttons_query_handler, \
    ITEM_DETAILS_MENU, WIKI_MAIN_MENU

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
START_MENU, CHARACTERS_CREATOR_MENU, WIKI_MENU = map(int, range(3))

STOPPING = 99

# bot data keys
BOT_DATA_CHAT_IDS = 'bot_data_chat_ids'

# chat data keys
WIKI = 'wiki'
CHARACTERS_CREATOR = 'characters_creator'
CURRENT_INLINE_PAGE_FOR_SUBMENUS = 'current_inline_page_for_submenu'
INLINE_PAGES = 'inline_pages'

# user data keys
ACTIVE_CONV = 'active_conv'

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
                                               "🟢 Il Bot è ripartito dopo un riavvio! Probabilmente ora è meglio di prima 🟢")
        except (BadRequest, TelegramError) as e:
            logger.error(f"CHAT_ID: {chat_id} Telegram error stopping the bot: {e}")


async def post_stop_callback(application: Application) -> None:
    for chat_id in application.bot_data.get(BOT_DATA_CHAT_IDS, []):
        try:
            await application.bot.send_message(chat_id,
                                               "🔴 Il bot si è spento... qualcuno è a lavoro! 🔴")
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
    await update.effective_message.reply_text('Ok! Usa il comando /start per avviare una nuova conversazione!\n')

    context.chat_data[WIKI] = {}
    context.user_data[ACTIVE_CONV] = None
    return ConversationHandler.END


async def stop_nested(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Ok! Usa i comandi:\n"
                                    "/wiki per consultare la wiki\n"
                                    "/character per usare il gestore di personaggi")
    context.chat_data[WIKI] = {}
    return STOPPING


async def handle_old_callback_queries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("This conversation is over or you didn't start it! Wait until it ends!", show_alert=True)


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

    # -------------------------------------------------- new
    equipment_categories_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(equipment_categories_first_menu_query_handler)],
        states={
            EQUIPMENT_CATEGORIES_SUBMENU: [CallbackQueryHandler(equipment_categories_first_menu_query_handler)],
            EQUIPMENT_VISUALIZATION: [CallbackQueryHandler(equipment_visualization_query_handler)]
        },
        fallbacks=[CommandHandler("stop", stop_nested)],
        map_to_parent={
            STOPPING: STOPPING
        },
        name='equipment_categories_handler_v2',
        persistent=True
    )

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
            CLASS_SUBMENU: CLASS_SUBMENU
        },
        name='class_options_handler_v3',
        persistent=True
    )

    wiki_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(wiki_main_menu_handler, pattern=r"^wiki$"),
            CommandHandler('wiki', wiki_main_menu_handler)
        ],
        states={
            WIKI_MAIN_MENU: [
                CallbackQueryHandler(main_menu_buttons_query_handler, pattern=r'^[^/]+$'),
                CommandHandler('wiki', wiki_main_menu_handler)
            ],
            ITEM_DETAILS_MENU: [CallbackQueryHandler(details_menu_buttons_query_handler)],
            CLASS_SUBMENU: [class_options_handler],
            EQUIPMENT_CATEGORIES_SUBMENU: [equipment_categories_handler]
        },
        fallbacks=[
            CommandHandler("stop", stop)
        ],
        name='wiki_handler_v3',
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
            HIT_POINTS_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, character_hit_points_handler)],
            FUNCTION_SELECTION: [
                CallbackQueryHandler(character_change_level_query_handler, pattern=r"^level_(up|down)$"),
                CallbackQueryHandler(character_level_change_class_choice_handler,
                                     pattern=fr"^{LEVEL_UP_CALLBACK_DATA}\|.*$|^{LEVEL_DOWN_CALLBACK_DATA}\|.*$"),
                CallbackQueryHandler(character_bag_query_handler, pattern=fr"^{BAG_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_spells_query_handler, pattern=fr"^{SPELLS_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_abilities_query_handler, pattern=fr"^{ABILITIES_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_spells_slots_query_handler,
                                     pattern=fr"^{SPELLS_SLOT_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_feature_point_query_handler,
                                     pattern=fr"^{FEATURE_POINTS_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_multiclassing_query_handler,
                                     pattern=fr"^{MULTICLASSING_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_deleting_query_handler,
                                     pattern=fr"^{DELETE_CHARACTER_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_damage_query_handler,
                                     pattern=fr"^{DAMAGE_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_healing_query_handler,
                                     pattern=fr"^{HEALING_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_hit_points_query_handler,
                                     pattern=fr"^{HIT_POINTS_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_long_rest_warning_query_handler,
                                     pattern=fr"^{LONG_REST_WARNING_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_short_rest_warning_query_handler,
                                     pattern=fr"^{SHORT_REST_WARNING_CALLBACK_DATA}$"),
                CallbackQueryHandler(dice_handler,
                                     pattern=fr"^{ROLL_DICE_MENU_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_creator_settings, pattern=fr"^{SETTINGS_CALLBACK_DATA}$"),
                CommandHandler('stop', character_creation_stop)
            ],
            DAMAGE_REGISTRATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, character_damage_registration_handler)
            ],
            HEALING_REGISTRATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, character_healing_value_check_or_registration_handler)
            ],
            OVER_HEALING_CONFIRMATION: [
                CallbackQueryHandler(character_over_healing_registration_query_handler,
                                     pattern=r'^[yn]$')
            ],
            HIT_POINTS_REGISTRATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, character_hit_points_registration_handler)
            ],
            LONG_REST: [
                CallbackQueryHandler(character_long_rest_query_handler,
                                     pattern=fr"^{LONG_REST_CALLBACK_DATA}$")
            ],
            SHORT_REST: [
                CallbackQueryHandler(character_short_rest_query_handler,
                                     pattern=fr"^{SHORT_REST_CALLBACK_DATA}$")
            ],
            CHARACTER_SELECTION: [
                CallbackQueryHandler(character_selection_query_handler),
                CommandHandler('newCharacter', character_creation_handler)
            ],
            CHARACTER_DELETION: [
                CallbackQueryHandler(character_deleting_answer_query_handler,
                                     pattern=fr"^{AFFERMATIVE_CHARACTER_DELETION_CALLBACK_DATA}|{NEGATIVE_CHARACTER_DELETION_CALLBACK_DATA}$")
            ],
            BAG_MANAGEMENT: [
                CallbackQueryHandler(character_bag_new_object_query_handler,
                                     pattern=fr"^{BAG_ITEM_INSERTION_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_bag_edit_object_query_handler, pattern=fr"^{BAG_ITEM_EDIT}$")
            ],
            BAG_ITEM_INSERTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, character_bag_item_insert)
            ],
            BAG_ITEM_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, character_bag_item_edit_handler),
                CallbackQueryHandler(character_bag_item_delete_one_handler,
                                     pattern=fr"^{BAG_ITEM_EDIT_CALLBACK_DATA}\|-"),
                CallbackQueryHandler(character_bag_item_add_one_handler,
                                     pattern=fr"^{BAG_ITEM_EDIT_CALLBACK_DATA}\|\+"),
                CallbackQueryHandler(character_bag_item_delete_all_handler,
                                     pattern=fr"^{BAG_ITEM_EDIT_CALLBACK_DATA}\|all"),
                CallbackQueryHandler(character_bag_ask_item_overwrite_quantity_query_handler,
                                     pattern=fr"^{BAG_ITEM_EDIT_CALLBACK_DATA}\|overwrite$")
            ],
            BAG_ITEM_OVERWRITE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, character_ask_item_overwrite_quantity)
            ],
            FEATURE_POINTS_EDIT: [
                CallbackQueryHandler(character_feature_points_edit_query_handler,
                                     pattern=r"^(strength|dexterity|constitution|intelligence|wisdom|charisma)\|[+-]$")
            ],
            ABILITIES_MENU: [
                CallbackQueryHandler(character_ability_new_query_handler,
                                     pattern=fr"^{SPELL_LEARN_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_abilities_menu_query_handler,
                                     pattern=fr"^(ability_name\|.+|prev_page|next_page)$")
            ],
            ABILITY_VISUALIZATION: [
                CallbackQueryHandler(character_ability_visualization_query_handler,
                                     pattern=fr"{ABILITY_EDIT_CALLBACK_DATA}|{ABILITY_DELETE_CALLBACK_DATA}|"
                                             fr"{ABILITY_ACTIVE_CALLBACK_DATA}|{ABILITY_USE_CALLBACK_DATA}"
                                             fr"|{ABILITY_BACK_MENU_CALLBACK_DATA}")
            ],
            ABILITY_ACTIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, character_ability_edit_handler),
                CallbackQueryHandler(character_ability_delete_query_handler,
                                     pattern=r'^[yn]$')
            ],
            ABILITY_LEARN: [
                CallbackQueryHandler(character_ability_insert_query_handler,
                                     pattern=fr"^{ABILITY_INSERT_CALLBACK_DATA}$"),
                CallbackQueryHandler(
                    character_ability_features_query_handler,
                    pattern=fr"^({ABILITY_IS_PASSIVE_CALLBACK_DATA}\|\d+|{ABILITY_RESTORATION_TYPE_CALLBACK_DATA}\|(short|long))$"
                ),
                CallbackQueryHandler(character_ability_new_query_handler,
                                     pattern=fr"^{ABILITY_LEARN_CALLBACK_DATA}$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, character_ability_text_handler)
            ],
            SPELLS_MENU: [
                CallbackQueryHandler(character_spells_menu_query_handler,
                                     pattern=fr"^(spell_name\|.+|prev_page|next_page|{SPELL_LEARN_CALLBACK_DATA})$")
            ],
            SPELL_VISUALIZATION: [
                CallbackQueryHandler(character_spell_visualization_query_handler,
                                     pattern=fr"{SPELL_EDIT_CALLBACK_DATA}|{SPELL_DELETE_CALLBACK_DATA}|"
                                             fr"{SPELL_BACK_MENU_CALLBACK_DATA}|{SPELL_USE_CALLBACK_DATA}")
            ],
            SPELL_ACTIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, character_spell_edit_handler),
                CallbackQueryHandler(character_spell_delete_query_handler,
                                     pattern=r'^[yn]$'),
                CallbackQueryHandler(character_spell_use_query_handler,
                                     pattern=fr"^{SPELL_USAGE_BACK_MENU_CALLBACK_DATA}|{SPELL_SLOT_SELECTED_CALLBACK_DATA}\|\d+$")
            ],
            SPELL_LEARN: [
                CallbackQueryHandler(character_spell_new_query_handler,
                                     pattern=fr"^{SPELL_LEARN_CALLBACK_DATA}$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, character_spell_learn_handler)
            ],
            MULTICLASSING_ACTIONS: [
                CallbackQueryHandler(character_multiclassing_add_class_query_handler,
                                     pattern=fr"^{MULTICLASSING_ADD_CALLBACK_DATA}$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, character_multiclassing_add_class_answer_handler),
                CallbackQueryHandler(character_multiclassing_remove_class_query_handler,
                                     pattern=fr"^{MULTICLASSING_REMOVE_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_multiclassing_remove_class_answer_query_handler,
                                     pattern=r"^remove\|.+$"),
                CallbackQueryHandler(character_multiclassing_reassign_levels_query_handler,
                                     pattern=r"^assign_levels\|.+\|\d+$")
            ],
            SPELLS_SLOTS_MANAGEMENT: [
                CallbackQueryHandler(character_spells_slots_mode_answer_query_handler,
                                     pattern=r"^spells_slot_(auto|manual)$"),
                CallbackQueryHandler(character_spells_slots_add_query_handler,
                                     pattern=fr"^{SPELLS_SLOTS_INSERT_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_spells_slots_remove_query_handler,
                                     pattern=fr"^{SPELLS_SLOTS_REMOVE_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_spells_slot_use_slot_query_handler,
                                     pattern=fr"^{SPELL_SLOT_SELECTED_CALLBACK_DATA}\|\d+$"),
                CallbackQueryHandler(character_spells_slot_use_reset_query_handler,
                                     pattern=fr"^{SPELLS_SLOTS_RESET_CALLBACK_DATA}$"),
                CallbackQueryHandler(character_spells_slot_change_mode_query_handler,
                                     pattern=fr"^{SPELLS_SLOTS_CHANGE_CALLBACK_DATA}$")
            ],
            SPELL_SLOT_ADDING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, character_spell_slot_add_answer_query_handler)
            ],
            SPELL_SLOT_REMOVING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, character_spell_slot_remove_answer_query_handler)
            ],
            DICE_ACTION: [
                CallbackQueryHandler(dice_actions_query_handler,
                                     pattern=fr"^(d\d+\|[+-]|{ROLL_DICE_CALLBACK_DATA}|{ROLL_DICE_DELETE_HISTORY_CALLBACK_DATA})$")
            ],
            SETTINGS_MENU_STATE: [
                CallbackQueryHandler(character_creator_settings_callback_handler)
            ]
        },
        fallbacks=[
            CommandHandler("stop", character_creator_stop_submenu),
            CallbackQueryHandler(character_generic_main_menu_query_handler)
        ],
        name='character_creator_handler_v13',
        persistent=True
    )

    main_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_handler)],
        states={
            START_MENU: [
                wiki_handler,
                character_creator_handler
            ]
        },
        fallbacks=[CommandHandler('stop', stop)],
        name='main_conversation_handler_v2',
        persistent=True
    )
    application.add_handler(main_conversation_handler)

    # Manage buttons pressing in old conversations
    application.add_handler(CallbackQueryHandler(handle_old_callback_queries))

    # Start the bot polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
