import asyncio
import logging
import os
import random
import re
from collections import defaultdict
from typing import List, Tuple, Dict, Any

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, File
from telegram.constants import ParseMode, ChatType, FileSizeLimit
from telegram.error import TelegramError
from telegram.ext import ContextTypes, ConversationHandler

from src.model.character_creator.Ability import Ability, RestorationType
from src.model.character_creator.Character import Character, SpellsSlotMode
from src.model.character_creator.Item import Item
from src.model.character_creator.MultiClass import MultiClass
from src.model.character_creator.Spell import Spell, SpellLevel
from src.model.character_creator.SpellSlot import SpellSlot
from src.util import chunk_list, generate_abilities_list_keyboard, generate_spells_list_keyboard, extract_3_words

logger = logging.getLogger(__name__)

CHARACTER_CREATOR_VERSION = "3.2.0"

# states definition
(CHARACTER_CREATION,
 CHARACTER_SELECTION,
 NAME_SELECTION,
 RACE_SELECTION,
 GENDER_SELECTION,
 CLASS_SELECTION,
 HIT_POINTS_SELECTION,
 FUNCTION_SELECTION,
 BAG_MANAGEMENT,
 CHARACTER_DELETION,
 BAG_ITEM_INSERTION,
 BAG_ITEM_EDIT,
 BAG_ITEM_OVERWRITE,
 FEATURE_POINTS_EDIT,
 ABILITIES_MENU,
 ABILITY_VISUALIZATION,
 ABILITY_ACTIONS,
 ABILITY_LEARN,
 SPELLS_MENU,
 SPELL_LEVEL_MENU,
 SPELL_VISUALIZATION,
 SPELL_ACTIONS,
 SPELL_LEARN,
 MULTICLASSING_ACTIONS,
 SPELLS_SLOTS_MANAGEMENT,
 SPELL_SLOT_ADDING,
 SPELL_SLOT_REMOVING,
 DAMAGE_REGISTRATION,
 HEALING_REGISTRATION,
 OVER_HEALING_CONFIRMATION,
 HIT_POINTS_REGISTRATION,
 LONG_REST,
 SHORT_REST,
 DICE_ACTION,
 NOTES_MANAGEMENT,
 NOTE_TEXT_ADD,
 MAPS_MANAGEMENT,
 MAPS_ZONE,
 MAPS_FILES,
 ADD_MAPS_FILES,
 SETTINGS_MENU_STATE) = map(int, range(14, 55))

STOPPING = 99

# bot data keys
BOT_DATA_CHAT_IDS = 'bot_data_chat_ids'

# user_data keys
# we use the user_data because this function is for private use only
CHARACTERS_CREATOR_KEY = 'characters_creator'
CHARACTERS_KEY = 'characters'
TEMP_CHARACTER_KEY = 'temp_character'
CURRENT_CHARACTER_KEY = 'current_character'
CURRENT_ITEM_KEY = 'current_item'
CURRENT_INLINE_PAGE_INDEX_KEY = 'current_page_index'
INLINE_PAGES_KEY = 'inline_pages'
CURRENT_ABILITY_KEY = 'current_ability'
ABILITY_FEATURES_KEY = 'ability_features_keyboard'
TEMP_ABILITY_KEY = 'temp_ability'
TEMP_HEALING_KEY = 'temp_healing'
CURRENT_SPELL_KEY = 'current_spell'
LAST_MENU_MESSAGES = 'last_menu_message'
# Keys to store the data allowing a rollback in the case user use /stop command before ending the multiclass deleting
PENDING_REASSIGNMENT = 'pending_reassignment'
REMOVED_CLASS_LEVEL = 'removed_class_level'
REMAINING_CLASSES = 'remaining_classes'
# spell slots
SPELL_SLOTS = 'spell_slots'
DICE = 'dice'
DICE_MESSAGES = 'dice_messages'
ACTIVE_CONV = 'active_conv'
# keys for maps
TEMP_ZONE_NAME = 'temp_zone_name'
TEMP_MAPS_PATHS = 'temp_maps_paths'
ADD_OR_INSERT_MAPS = 'add_or_insert_maps'
# keys for settings
USER_SETTINGS_KEY = 'user_settings'
SPELL_MANAGEMENT_KEY = 'spell_management'

# character callback keys
BACK_BUTTON_CALLBACK_DATA = "back_button"
BAG_CALLBACK_DATA = 'bag'
SPELLS_CALLBACK_DATA = 'spells'
ABILITIES_CALLBACK_DATA = 'abilities'
FEATURE_POINTS_CALLBACK_DATA = 'feature_points'
SPELLS_SLOT_CALLBACK_DATA = 'spells_slot'
MULTICLASSING_CALLBACK_DATA = 'multiclass'
DELETE_CHARACTER_CALLBACK_DATA = 'delete_character'
AFFERMATIVE_CHARACTER_DELETION_CALLBACK_DATA = 'yes_delete_character'
NEGATIVE_CHARACTER_DELETION_CALLBACK_DATA = 'no_delete_character'
BAG_ITEM_INSERTION_CALLBACK_DATA = "bag_insert_item"
BAG_ITEM_EDIT_CALLBACK_DATA = "bag_edit_item"
ABILITY_LEARN_CALLBACK_DATA = "ability_learn"
ABILITY_EDIT_CALLBACK_DATA = "ability_edit"
ABILITY_DELETE_CALLBACK_DATA = "ability_delete"
ABILITY_USE_CALLBACK_DATA = "ability_use"
ABILITY_ACTIVE_CALLBACK_DATA = 'ability_active'
ABILITY_BACK_MENU_CALLBACK_DATA = "ability_back_menu"
ABILITY_IS_PASSIVE_CALLBACK_DATA = "ability_is_passive"
ABILITY_RESTORATION_TYPE_CALLBACK_DATA = "ability_restoration_type"
ABILITY_INSERT_CALLBACK_DATA = "ability_insert"
SPELL_LEARN_CALLBACK_DATA = "spells_learn"
SPELL_EDIT_CALLBACK_DATA = "spell_edit"
SPELL_USE_CALLBACK_DATA = "spell_use"
SPELL_DELETE_CALLBACK_DATA = "spell_delete"
SPELL_BACK_MENU_CALLBACK_DATA = "spell_back_menu"
SPELL_USAGE_BACK_MENU_CALLBACK_DATA = "spell_usage_back_menu"
LEVEL_UP_CALLBACK_DATA = "level_up"
LEVEL_DOWN_CALLBACK_DATA = "level_down"
DAMAGE_CALLBACK_DATA = "damage"
HEALING_CALLBACK_DATA = "healing"
HIT_POINTS_CALLBACK_DATA = "hit_points"
MULTICLASSING_ADD_CALLBACK_DATA = "add_multiclass"
MULTICLASSING_REMOVE_CALLBACK_DATA = "remove_multiclass"
SPELL_SLOTS_AUTO_CALLBACK_DATA = "spells_slot_auto"
SPELL_SLOTS_MANUAL_CALLBACK_DATA = "spells_slot_manual"
SPELLS_SLOTS_CHANGE_CALLBACK_DATA = "spells_slot_change"
SPELLS_SLOTS_RESET_CALLBACK_DATA = "spells_slot_reset"
SPELLS_SLOTS_REMOVE_CALLBACK_DATA = "spells_slot_remove"
SPELLS_SLOTS_INSERT_CALLBACK_DATA = "spells_slot_insert"
SPELL_SLOT_SELECTED_CALLBACK_DATA = "spell_slot_selected"
SPELL_SLOT_LEVEL_SELECTED_CALLBACK_DATA = "spell_slot_level"
LONG_REST_WARNING_CALLBACK_DATA = "long_rest_warning"
LONG_REST_CALLBACK_DATA = "long_rest"
SHORT_REST_WARNING_CALLBACK_DATA = "short_rest_warning"
SHORT_REST_CALLBACK_DATA = "short_rest"
ROLL_DICE_MENU_CALLBACK_DATA = "roll_dice_menu"
ROLL_DICE_CALLBACK_DATA = "roll_dice"
ROLL_DICE_DELETE_HISTORY_CALLBACK_DATA = "roll_dice_history_delete"
NOTES_CALLBACK_DATA = "notes"
INSERT_NEW_NOTE_CALLBACK_DATA = "insert_new_note"
OPEN_NOTE_CALLBACK_DATA = "open_note"
EDIT_NOTE_CALLBACK_DATA = "edit_note"
DELETE_NOTE_CALLBACK_DATA = "delete_note"
MAPS_CALLBACK_DATA = "maps"
SHOW_MAPS_CALLBACK_DATA = "show_maps"
INSERT_NEW_MAPS_CALLBACK_DATA = "insert_new_maps"
DELETE_SINGLE_MAP_CALLBACK_DATA = "delete_single_map"
ADD_NEW_MAP_CALLBACK_DATA = "add_new_map"
DELETE_ALL_ZONE_MAPMS_CALLBACK_DATA = "delete_all_zone_mapms"
SETTINGS_CALLBACK_DATA = "settings"

# Setting related callback
SETTING_SPELL_MANAGEMENT_CALLBACK_DATA = 'setting_spell_management'
# Spells management
SPELL_MANAGEMENT_PAGINATE_BY_LEVEL = 'paginate_by_level'
SPELL_MANAGEMENT_SELECT_LEVEL_DIRECTLY = 'select_level_directly'

STARTING_DICE = {
    'd4': 0,
    'd6': 0,
    'd8': 0,
    'd100': 0,
    'd10': 0,
    'd12': 0,
    'd20': 0
}
ROLLS_MAP = {
    'd4': 4,
    'd6': 6,
    'd8': 8,
    'd100': 100,
    'd10': 10,
    'd12': 12,
    'd20': 20
}

# Definition of settings and their options
SETTINGS = [
    {
        'key': 'spell_management',
        'title': 'Gestione delle spell',
        'description': 'Seleziona la modalità di gestione delle spell:',
        'options': [
            {'value': 'paginate_by_level', 'text': 'Paginazione per livello spell'},
            {'value': 'select_level_directly', 'text': 'Selezione diretta del livello spell'}
        ]
    }
]

FILES_DIR_PATH = 'files/'
MAPS_DIR_PATH = FILES_DIR_PATH + 'maps'


async def send_and_save_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs):
    """Wrapper for reply_text that saves the last message in user_data."""
    message = await update.effective_message.reply_text(text, **kwargs)

    # Check if the mailing list already exists, if not, create it
    if LAST_MENU_MESSAGES not in context.user_data[CHARACTERS_CREATOR_KEY]:
        context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES] = []

    # Add new message to the list
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(message)

    return message


def create_main_menu_message(character: Character) -> Tuple[str, InlineKeyboardMarkup]:
    if character.current_hit_points <= -character.hit_points:
        health_str = '☠️\n'
    else:
        health_str = f"{character.current_hit_points if character.current_hit_points <= character.hit_points else character.hit_points}/{character.hit_points} PF\n"
        f"{f'({(character.current_hit_points - character.hit_points)} Punti ferita temporanei)\n' if character.current_hit_points > character.hit_points else '\n'}"

    message_str = (f"Benvenuto nella gestione personaggio! v.{CHARACTER_CREATOR_VERSION}\n"
                   f"<b>Nome personaggio:</b> {character.name} L. {character.total_levels()}\n"
                   f"<b>Razza:</b> {character.race}\n"
                   f"<b>Genere:</b> {character.gender}\n"
                   f"<b>Classe:</b> {', '.join(f"{class_name} (Level {level})" for class_name, level in character.multi_class.classes.items())}\n"
                   f"<b>Punti ferita:</b> {health_str}"
                   f"<b>Peso trasportato:</b> {character.encumbrance} Lb\n\n"
                   f"<b>Punti caratteristica</b>\n<code>{str(character.feature_points)}\n\n</code>"
                   f"<b>Slot incantesimo</b>\n{"\n".join([f"L{str(slot.level)}  {"🟥" * slot.used_slots}{"🟦" * (slot.total_slots - slot.used_slots)}" for _, slot in sorted(character.spell_slots.items())]) if character.spell_slots else "Non hai registrato ancora nessuno Slot incantesimo"}\n\n"
                   f"<b>Abilità passive attivate:</b>\n{'\n'.join(ability.name for ability in character.abilities if ability.activated) if any(ability.activated for ability in character.abilities) else 'Nessuna abilità attiva'}\n")

    keyboard = [
        [
            InlineKeyboardButton('⬇️ Level down', callback_data=LEVEL_DOWN_CALLBACK_DATA),
            InlineKeyboardButton('⬆️ Level up', callback_data=LEVEL_UP_CALLBACK_DATA)
        ],
        [
            InlineKeyboardButton('💔 Prendi danni', callback_data=DAMAGE_CALLBACK_DATA),
            InlineKeyboardButton('❤️‍🩹 Curati', callback_data=HEALING_CALLBACK_DATA)
        ],
        [
            InlineKeyboardButton('🧬 Gestisci punti ferita 💉', callback_data=HIT_POINTS_CALLBACK_DATA)
        ],
        [
            InlineKeyboardButton('🧳 Borsa', callback_data=BAG_CALLBACK_DATA),
            InlineKeyboardButton('🗯 Azioni', callback_data=ABILITIES_CALLBACK_DATA),
            InlineKeyboardButton('📖 Spell', callback_data=SPELLS_CALLBACK_DATA)
        ],
        [InlineKeyboardButton('🔮 Gestisci slot incantesimo', callback_data=SPELLS_SLOT_CALLBACK_DATA)],
        [InlineKeyboardButton('🧮 Punti caratteristica', callback_data=FEATURE_POINTS_CALLBACK_DATA)],
        [InlineKeyboardButton('🪓🛡🪄 Gestisci multiclasse', callback_data=MULTICLASSING_CALLBACK_DATA)],
        [
            InlineKeyboardButton('🌙 Riposo lungo', callback_data=LONG_REST_WARNING_CALLBACK_DATA),
            InlineKeyboardButton('🍻 Riposo breve', callback_data=SHORT_REST_WARNING_CALLBACK_DATA)
        ],
        [InlineKeyboardButton('🎲 Lancia Dado', callback_data=ROLL_DICE_MENU_CALLBACK_DATA)],
        [
            InlineKeyboardButton('🗒 Note', callback_data=NOTES_CALLBACK_DATA),
            InlineKeyboardButton('🗺 Mappe', callback_data=MAPS_CALLBACK_DATA)
        ],
        [InlineKeyboardButton('⚙️ Impostazioni', callback_data=SETTINGS_CALLBACK_DATA)],
        [InlineKeyboardButton('🗑️ Elimina personaggio', callback_data=DELETE_CHARACTER_CALLBACK_DATA)]
    ]

    return message_str, InlineKeyboardMarkup(keyboard)


def create_ability_keyboard(features_chosen: Dict[str, str | bool]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f'Abilità passiva {'✅' if features_chosen['is_passive'] else '❌'}',
                callback_data=f'{ABILITY_IS_PASSIVE_CALLBACK_DATA}|1'),
            InlineKeyboardButton(
                f'Abilità attiva {'✅' if not features_chosen['is_passive'] else '❌'}',
                callback_data=f'{ABILITY_IS_PASSIVE_CALLBACK_DATA}|0'),
        ],
        [
            InlineKeyboardButton(
                f'Riposo breve {'✅' if features_chosen['restoration_type'] == RestorationType.SHORT_REST else '❌'}',
                callback_data=f'{ABILITY_RESTORATION_TYPE_CALLBACK_DATA}|short'
            ),
            InlineKeyboardButton(
                f'Riposo lungo {'✅' if features_chosen['restoration_type'] == RestorationType.LONG_REST else '❌'}',
                callback_data=f'{ABILITY_RESTORATION_TYPE_CALLBACK_DATA}|long'
            )
        ],
        [
            InlineKeyboardButton('Impara abilità', callback_data=ABILITY_INSERT_CALLBACK_DATA)
        ]
    ])


def create_feature_points_messages(feature_points: Dict[str, int]) -> Dict[str, Tuple[str, InlineKeyboardMarkup]]:
    return {
        'strength': (
            f"<code>Forza        {' ' if feature_points['strength'] < 10 else ''}{feature_points['strength']}</code>",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("-", callback_data="strength|-"),
                    InlineKeyboardButton("+", callback_data="strength|+")
                ]
            ])
        ),
        'dexterity': (
            f"<code>Destrezza    {' ' if feature_points['dexterity'] < 10 else ''}{feature_points['dexterity']}</code>",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("-", callback_data="dexterity|-"),
                    InlineKeyboardButton("+", callback_data="dexterity|+")
                ]
            ])
        ),
        'constitution': (
            f"<code>Costituzione {' ' if feature_points['constitution'] < 10 else ''}{feature_points['constitution']}</code>",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("-", callback_data="constitution|-"),
                    InlineKeyboardButton("+", callback_data="constitution|+")
                ]
            ])
        ),
        'intelligence': (
            f"<code>Intelligenza {' ' if feature_points['intelligence'] < 10 else ''}{feature_points['intelligence']}</code>",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("-", callback_data="intelligence|-"),
                    InlineKeyboardButton("+", callback_data="intelligence|+")
                ]
            ])
        ),
        'wisdom': (
            f"<code>Saggezza     {' ' if feature_points['wisdom'] < 10 else ''}{feature_points['wisdom']}</code>",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("-", callback_data="wisdom|-"),
                    InlineKeyboardButton("+", callback_data="wisdom|+")
                ]
            ])
        ),
        'charisma': (
            f"<code>Carisma      {' ' if feature_points['charisma'] < 10 else ''}{feature_points['charisma']}</code>",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("-", callback_data="charisma|-"),
                    InlineKeyboardButton("+", callback_data="charisma|+")
                ]
            ])
        )
    }


def create_spell_slots_menu(context: ContextTypes.DEFAULT_TYPE):
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    message_str = (f"Seleziona i pulsanti con gli slot liberi 🟦 per utilizzare uno slot del livello corrispondente.\n\n"
                   f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione")
    keyboard = []
    if not character.spell_slots:

        message_str += "Non hai ancora nessuno slot incantesimo"

    else:

        spell_slots_buttons = []

        # Sort slots by level (dictionary key)
        for level, slot in sorted(character.spell_slots.items()):
            spell_slots_buttons.append(InlineKeyboardButton(
                f"{str(slot.level)} {'🟥' * slot.used_slots}{'🟦' * (slot.total_slots - slot.used_slots)}",
                callback_data=f"{SPELL_SLOT_SELECTED_CALLBACK_DATA}|{slot.level}"))

        # Group buttons into rows of maximum 3 buttons each
        for slot in spell_slots_buttons:
            keyboard.append([slot])

    keyboard.append(
        [
            InlineKeyboardButton("Inserisci nuovo slot", callback_data=SPELLS_SLOTS_INSERT_CALLBACK_DATA),
            InlineKeyboardButton("Rimuovi slot", callback_data=SPELLS_SLOTS_REMOVE_CALLBACK_DATA),
        ]
    )
    keyboard.append(
        [
            InlineKeyboardButton("Resetta utilizzi slot", callback_data=SPELLS_SLOTS_RESET_CALLBACK_DATA)
        ]
    )
    keyboard.append(
        [
            InlineKeyboardButton("Cambia modalità", callback_data=SPELLS_SLOTS_CHANGE_CALLBACK_DATA)
        ]
    )

    return message_str, InlineKeyboardMarkup(keyboard)


def create_spell_slots_menu_for_spell(character: Character, spell: Spell) -> Tuple[str, InlineKeyboardMarkup]:
    keyboard = []
    message_str = (
        "Seleziona i pulsanti con gli slot liberi 🟦 per utilizzare un incantesimo del livello corrispondente al livello dello slot utilizzato.\n\n"
        "Usa /stop per terminare o un bottone del menù principale per cambiare funzione")

    if not character.spell_slots:

        message_str += ("Non hai ancora nessuno slot incantesimo!\n"
                        "Usa il menu <i><b>Gestisci slot incantesimo</b></i> per aggiungerli")

    else:

        spell_slots_buttons = []

        # Sort slots by level (dictionary key)
        for level, slot in sorted(character.spell_slots.items()):
            if level >= spell.level.value:
                spell_slots_buttons.append(InlineKeyboardButton(
                    f"{str(slot.level)} {'🟥' * slot.used_slots}{'🟦' * (slot.total_slots - slot.used_slots)}",
                    callback_data=f"{SPELL_SLOT_SELECTED_CALLBACK_DATA}|{slot.level}"))

        # Group buttons into rows of maximum 3 buttons each
        for slot in spell_slots_buttons:
            keyboard.append([slot])

        if not keyboard:
            message_str += f"Non hai slot incantesimo del livello necessario a castare questa spell!"

    keyboard.append([InlineKeyboardButton("Indietro 🔙", callback_data=SPELL_USAGE_BACK_MENU_CALLBACK_DATA)])

    return message_str, InlineKeyboardMarkup(keyboard)


def create_bag_menu(character: Character) -> Tuple[str, InlineKeyboardMarkup]:
    # Determine the max length of the quantity string for alignment
    max_quantity_length = max((len(str(item.quantity)) for item in character.bag), default=0)

    # Create the message string with aligned quantities
    message_str = (
        f"<b>Oggetti nella borsa</b>\n"
        f"<b>Peso trasportabile massimo</b> {character.carry_capacity}Lb\n\n"
        f"{''.join(f'<code>• Pz {str(item.quantity).ljust(max_quantity_length)}</code>   <code>{item.name}</code>\n' for item in character.bag) if character.bag else 'Lo zaino è ancora vuoto'}\n\n"
        f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione"
    )

    # Create the keyboard with action buttons
    keyboard = [[InlineKeyboardButton('Inserisci nuovo oggetto', callback_data=BAG_ITEM_INSERTION_CALLBACK_DATA)]]

    if character.bag:
        keyboard.append([InlineKeyboardButton('Modifica oggetto', callback_data=BAG_ITEM_EDIT)])

    return message_str, InlineKeyboardMarkup(keyboard)


def create_item_menu(item: Item) -> Tuple[str, InlineKeyboardMarkup]:
    message_str = (f"<b>{item.name:<{50}}</b>{item.quantity}Pz\n\n"
                   f"<b>Descrizione</b>\n{item.description}\n\n"
                   f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n")

    keyboard = [
        [
            InlineKeyboardButton("-", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|-"),
            InlineKeyboardButton("+", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|+")
        ],
        [InlineKeyboardButton('Sovrascrivi quantità', callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|overwrite")],
        [InlineKeyboardButton("Rimuovi tutti", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|all")]
    ]

    return message_str, InlineKeyboardMarkup(keyboard)


def create_spell_menu(spell: Spell) -> Tuple[str, InlineKeyboardMarkup]:
    message_str = (f"<b>{spell.name:<{50}}</b>L{spell.level.value}\n\n"
                   f"<b>Descrizione</b>\n{spell.description}\n\n"
                   f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione")
    keyboard = [
        [InlineKeyboardButton("Usa", callback_data=SPELL_USE_CALLBACK_DATA)],
        [InlineKeyboardButton("Modifica", callback_data=SPELL_EDIT_CALLBACK_DATA),
         InlineKeyboardButton("Dimentica", callback_data=SPELL_DELETE_CALLBACK_DATA)],
        [InlineKeyboardButton("Indietro 🔙", callback_data=SPELL_BACK_MENU_CALLBACK_DATA)]
    ]

    return message_str, InlineKeyboardMarkup(keyboard)


async def create_spells_menu(character: Character, update: Update, context: ContextTypes.DEFAULT_TYPE,
                             edit_mode: bool = False) -> int:
    message_str = f"<b>Gestione spells</b>\nUsa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
    if not character.spells:

        message_str += "Non conosci ancora nessun incantesimo ‍🤷‍♂️"
        keyboard = [
            [InlineKeyboardButton("Impara nuovo incantesimo", callback_data=SPELL_LEARN_CALLBACK_DATA)]
        ]

        if edit_mode:
            await update.effective_message.edit_text(message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                                     parse_mode=ParseMode.HTML)
        else:
            await send_and_save_message(update, context, message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                        parse_mode=ParseMode.HTML)

        return SPELL_LEARN

    else:

        message_str += "Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n"

    spells = character.spells

    # Group spells by level
    level_to_spells = defaultdict(list)
    for spell in spells:
        level_to_spells[spell.level.value].append(spell)

    # Create pages as a list of tuples (level, spells of that level)
    levels = sorted(level_to_spells.keys())
    pages = []
    for level in levels:
        pages.append((level, level_to_spells[level]))

    # Save pages in user context
    context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY] = pages
    context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] = 0

    # Get the current page
    current_page_index = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]
    current_page = pages[current_page_index]
    level, spells_in_page = current_page

    message_str += f"Ecco la lista degli incantesimi di livello {level}"

    # Generates the keyboard for spells on the current page
    reply_markup = generate_spells_list_keyboard(spells_in_page)
    if edit_mode:
        await update.effective_message.edit_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELLS_MENU


async def create_spell_levels_menu(character: Character, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   edit_mode: bool = False) -> int:
    message_str = f"<b>Gestione spells</b>\nUsa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"

    if not character.spells:
        message_str += "Non conosci ancora nessun incantesimo ‍🤷‍♂️"
        keyboard = [
            [InlineKeyboardButton("Impara nuovo incantesimo", callback_data=SPELL_LEARN_CALLBACK_DATA)]
        ]

        if edit_mode:
            await update.effective_message.edit_text(message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                                     parse_mode=ParseMode.HTML)
        else:
            await send_and_save_message(update, context, message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                        parse_mode=ParseMode.HTML)

        return SPELL_LEARN

    else:

        message_str += "Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n"

    spells = character.spells
    buttons = []

    # Group spells by their level
    spells_by_level = {}
    # generate keyboared with spell level

    for spell in spells:
        spells_by_level.setdefault(spell.level.value, []).append(spell)

    # Iterate over the available spell levels (from 1 to 9)
    for level in SpellLevel:
        spell_level = level.value

        # Check if there is at least one spell of this level
        if spell_level in spells_by_level:
            # Check if slots are available for this level
            spell_slot = character.spell_slots.get(spell_level)
            if spell_slot:
                if spell_slot.slots_remaining() > 0:
                    button_text = f"Level {spell_level}"
                else:
                    button_text = f"Level {spell_level} ❌"

                buttons.append(
                    InlineKeyboardButton(button_text, callback_data=f"spell_of_level|{spell_level}")
                )

    # Return the keyboard with buttons in rows
    keyboard = [[button] for button in buttons]
    keyboard.append([InlineKeyboardButton("Impara nuovo incantesimo", callback_data=SPELL_LEARN_CALLBACK_DATA)])
    keyboard = InlineKeyboardMarkup(keyboard)

    if edit_mode:
        await update.effective_message.edit_text(message_str, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await send_and_save_message(update, context, message_str, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    return SPELL_LEVEL_MENU


async def create_abilities_menu(character: Character, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_str = f"<b>Gestione abilità</b>\nUsa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
    if not character.abilities:

        message_str += "Non hai ancora nessuna azione 🤷‍♂️"
        keyboard = [
            [InlineKeyboardButton("Impara nuova azione", callback_data=ABILITY_LEARN_CALLBACK_DATA)]
        ]
        await send_and_save_message(update, context, message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                    parse_mode=ParseMode.HTML)

        return ABILITY_LEARN

    else:
        message_str += ("Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n"
                        "Ecco la lista delle azioni")

    abilities = character.abilities
    abilities_pages = chunk_list(abilities, 10)

    context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY] = abilities_pages
    context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] = 0
    current_page = abilities_pages[context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]]

    reply_markup = generate_abilities_list_keyboard(current_page)

    await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return ABILITIES_MENU


def create_ability_menu(ability: Ability) -> Tuple[str, InlineKeyboardMarkup]:
    message_str = (f"<b>{ability.name}</b>\n\n"
                   f"<b>Descrizione</b>\n{ability.description}\n\n"
                   f"<b>Usi</b> {ability.uses}x\n\n"
                   f"<i>Azione {'passiva' if ability.is_passive else 'attiva'}, si ricarica con un riposo "
                   f"{'breve' if ability.restoration_type == RestorationType.SHORT_REST else 'lungo'}</i>")
    message_str += '\n\nUsa /stop per terminare o un bottone del menù principale per cambiare funzione'
    keyboard = [
        [
            InlineKeyboardButton("Modifica", callback_data=ABILITY_EDIT_CALLBACK_DATA),
            InlineKeyboardButton("Dimentica", callback_data=ABILITY_DELETE_CALLBACK_DATA)
        ]
    ]

    if ability.is_passive:
        second_row = [InlineKeyboardButton(f'{'Attiva' if not ability.activated else 'Disattiva'}',
                                           callback_data=ABILITY_ACTIVE_CALLBACK_DATA)]
    else:
        second_row = [InlineKeyboardButton('Usa', callback_data=ABILITY_USE_CALLBACK_DATA)]

    keyboard.append(second_row)
    keyboard.append([InlineKeyboardButton("Indietro 🔙", callback_data=ABILITY_BACK_MENU_CALLBACK_DATA)])

    return message_str, InlineKeyboardMarkup(keyboard)


def create_dice_keyboard(selected_dice: Dict[str, int]) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(f"{selected_dice['d4']} D4", callback_data=f"d4|+"),
            InlineKeyboardButton(f"{selected_dice['d6']} D6", callback_data=f"d6|+"),
            InlineKeyboardButton(f"{selected_dice['d8']} D8", callback_data=f"d8|+")
        ],
        [
            InlineKeyboardButton(f"-", callback_data=f"d4|-"),
            InlineKeyboardButton(f"-", callback_data=f"d6|-"),
            InlineKeyboardButton(f"-", callback_data=f"d8|-")
        ],
        [
            InlineKeyboardButton(f"{selected_dice['d10']} D10", callback_data=f"d10|+"),
            InlineKeyboardButton(f"{selected_dice['d12']} D12", callback_data=f"d12|+"),
            InlineKeyboardButton(f"{selected_dice['d100']} D100", callback_data=f"d100|+")
        ],
        [
            InlineKeyboardButton(f"-", callback_data=f"d10|-"),
            InlineKeyboardButton(f"-", callback_data=f"d12|-"),
            InlineKeyboardButton(f"-", callback_data=f"d100|-")
        ],
        [
            InlineKeyboardButton(f"{selected_dice['d20']} D20", callback_data=f"d20|+")
        ],
        [
            InlineKeyboardButton(f"-", callback_data=f"d20|-"),
        ]
    ]

    roll_text = 'Seleziona un dado' if sum(
        selected_dice.values()) == 0 else f'Lancia {', '.join([f'{roll_to_do}{die}' for die, roll_to_do in selected_dice.items() if roll_to_do > 0])}'
    keyboard.append([InlineKeyboardButton(roll_text, callback_data=ROLL_DICE_CALLBACK_DATA)])
    keyboard.append(
        [InlineKeyboardButton(f"Cancella cronologia", callback_data=ROLL_DICE_DELETE_HISTORY_CALLBACK_DATA)])

    return InlineKeyboardMarkup(keyboard)


def create_skull_asciart() -> str:
    return r"""<code>
           ______
        .-"      "-.
       /            \
      |              |
      |,  .-.  .-.  ,|
      | )(_o/  \o_)( |
      |/     /\     \|
      (_     ^^     _)
       \__|IIIIII|__/
        | \IIIIII/ |
        \          /
         `--------`
         
     SSSSS   EEEEE  III       
     S       E       I 
     SSS     EEEE    I
         S   E       I
     SSSSS   EEEEE  III        

M   M   OOO   RRRR  TTTTT  OOO
MM MM  O   O  R   R   T   O   O
M M M  O   O  RRRR    T   O   O
M   M  O   O  R  R    T   O   O
M   M   OOO   R   R   T    OOO</code>"""


def create_notes_menu(character: Character) -> Tuple[str, InlineKeyboardMarkup]:
    message_str = "<b>Note dell'avventura</b>\n\n"
    keyboard = []

    if not character.notes:
        message_str += "Non ci sono ancora delle note memorizzate 🤷‍♂️"

    else:
        message_str += ("Seleziona una nota da visualizzare premendo i pulsanti sottostanti o inseriscine una nuova "
                        "premendo il pulsante <b><i>\"Inserisci nuova nota\"</i></b>\n\n"
                        "Usa /stop per terminare o un bottone del menù principale per cambiare funzione")

        for title, note in character.notes.items():
            keyboard.append([InlineKeyboardButton(title, callback_data=f"{OPEN_NOTE_CALLBACK_DATA}|{title}")])

    keyboard.append([InlineKeyboardButton('Inserisci nuova nota', callback_data=INSERT_NEW_NOTE_CALLBACK_DATA)])

    return message_str, InlineKeyboardMarkup(keyboard)


def create_maps_menu(character: Character) -> Tuple[str, InlineKeyboardMarkup]:
    message_str = "<b>Mappe del mondo</b>\n\n"
    keyboard = []

    if not character.maps:
        message_str += "Non ci sono ancora delle mappe memorizzate 🤷‍♂️"

    else:
        message_str += ("Seleziona una zona da visualizzare premendo i pulsanti sottostanti o inseriscine una nuova "
                        "premendo il pulsante <b><i>\"Inserisci nuove mappe\"</i></b>\n\n"
                        "Usa /stop per terminare o un bottone del menù principale per cambiare funzione")

        for zone, maps_paths in character.maps.items():
            keyboard.append([InlineKeyboardButton(zone, callback_data=(zone, maps_paths))])

    keyboard.append([InlineKeyboardButton('Inserisci nuove mappe', callback_data=INSERT_NEW_MAPS_CALLBACK_DATA)])

    return message_str, InlineKeyboardMarkup(keyboard)


def verify_selected_map_callback_data(callback_data: Any) -> bool:
    return True if isinstance(callback_data, tuple) else False


def generate_settings_menu_single_message(user_settings):
    message_lines = []
    keyboard_buttons = []

    for setting in SETTINGS:
        key = setting['key']
        title = setting['title']
        description = setting['description']
        options = setting['options']

        # Ottieni la selezione corrente dell'utente
        current_value = user_settings.get(key, options[0]['value'])

        # Aggiungi il titolo e la descrizione al messaggio
        message_lines.append(f"<b>{title}</b>\n{description}")

        # Crea i pulsanti delle opzioni
        option_buttons = []
        for option in options:
            option_text = option['text']
            if option['value'] == current_value:
                option_text = '✅ ' + option_text

            callback_data = f'setting|{key}|{option["value"]}'
            option_buttons.append(InlineKeyboardButton(option_text, callback_data=callback_data))

        keyboard_buttons.append(option_buttons)

    message_text = '\n\n'.join(message_lines)
    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    return message_text, keyboard


async def character_creator_stop_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Rollback for multiclass management
    if PENDING_REASSIGNMENT in context.user_data[CHARACTERS_CREATOR_KEY]:
        # Get the pending reassignment information
        pending_reassignment = context.user_data[CHARACTERS_CREATOR_KEY][PENDING_REASSIGNMENT]
        removed_class_level = pending_reassignment[REMOVED_CLASS_LEVEL]
        remaining_classes = pending_reassignment[REMAINING_CLASSES]

        if len(remaining_classes) == 1:
            # Automatically reassign levels if only one class is left
            remaining_class_name = remaining_classes[0]
            character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
            multi_class = character.multi_class

            multi_class.add_class(remaining_class_name, removed_class_level)

            message_str = f"Il comando /stop è stato ricevuto.\n" \
                          f"I {removed_class_level} livelli rimossi sono stati aggiunti automaticamente alla classe {remaining_class_name}."
            await send_and_save_message(update, context, message_str, parse_mode=ParseMode.HTML)
        else:
            # Ask the user to finish reassigning the levels before stopping
            await send_and_save_message(update, context,
                                        "Devi assegnare i livelli rimanenti prima di poter usare il comando /stop.",
                                        parse_mode=ParseMode.HTML)
            return MULTICLASSING_ACTIONS

    else:

        if CURRENT_CHARACTER_KEY in context.user_data[CHARACTERS_CREATOR_KEY]:
            character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

            # Delete messages sent by bot and user
            messages = context.user_data[CHARACTERS_CREATOR_KEY].get(LAST_MENU_MESSAGES, [])
            for message in messages:
                try:
                    await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
                except TelegramError as e:
                    logger.warning(f"Errore durante la cancellazione del messaggio: {e}")
            context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].clear()

            msg, reply_markup = create_main_menu_message(character)
            await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

        else:

            await send_and_save_message(update, context,
                                        'Ok! Usa il comando /start per avviare una nuova conversazione!\n'
                                        'Oppure invia direttamente i comandi /wiki o /character',
                                        parse_mode=ParseMode.HTML)
            return ConversationHandler.END

        context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_CHARACTER_KEY, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ITEM_KEY, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(PENDING_REASSIGNMENT, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(ABILITY_FEATURES_KEY, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_ABILITY_KEY, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ABILITY_KEY, None)

        return FUNCTION_SELECTION


async def character_creation_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await send_and_save_message(update, context, 'Ok! Usa il comando /start per avviare una nuova conversazione!\n'
                                                 'Oppure invia direttamente i comandi /wiki o /character',
                                parse_mode=ParseMode.HTML)

    context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_CHARACTER_KEY, None)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ITEM_KEY, None)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(PENDING_REASSIGNMENT, None)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(ABILITY_FEATURES_KEY, None)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_ABILITY_KEY, None)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ABILITY_KEY, None)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_CHARACTER_KEY, None)

    context.user_data[ACTIVE_CONV] = None

    return ConversationHandler.END


async def character_creator_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        query = update.callback_query
        await query.answer()

    # Check if the user is already in another conversation
    if context.user_data.get(ACTIVE_CONV) == 'wiki':
        await update.effective_message.reply_text(
            "Usare /stop per uscire dalla wiki prima di usare la gestione dei personaggi.",
                                    parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    context.user_data[ACTIVE_CONV] = 'character'

    # Check for BOT_DATA_CHAT_IDS initialization
    if BOT_DATA_CHAT_IDS not in context.bot_data or update.effective_chat.id not in context.bot_data.get(
            BOT_DATA_CHAT_IDS, []):
        await update.effective_message.reply_text("La prima volta devi interagire con il bot usando il comando /start",
                                    parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    # check if the function is called in a group or not
    if update.effective_chat.type != ChatType.PRIVATE:
        await update.effective_message.reply_text(
            "La funzione di gestione del personaggio può essere usata solo in privato!\n"
                                    "Ritorno al menù principale...",
                                    parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    message_str = f"Benvenuto nella gestione del personaggio!\n"

    # check if the user has the character creator DB
    if CHARACTERS_CREATOR_KEY not in context.user_data:
        context.user_data[CHARACTERS_CREATOR_KEY] = {}

    # check if the user has already some characters created
    if CHARACTERS_KEY not in context.user_data[CHARACTERS_CREATOR_KEY] or not context.user_data[CHARACTERS_CREATOR_KEY][
        CHARACTERS_KEY]:
        message_str += (f"{update.effective_user.name} sembra che non hai inserito ancora nessun personaggio!\n\n"
                        f"Usa il comando /newCharacter per crearne uno nuovo o /stop per terminare la conversazione.")

        await update.effective_message.reply_text(message_str, parse_mode=ParseMode.HTML)
        return CHARACTER_CREATION

    else:
        characters: List[Character] = context.user_data[CHARACTERS_CREATOR_KEY][CHARACTERS_KEY]
        message_str += "Seleziona uno dei personaggi da gestire o creane uno nuovo con /newCharacter:"
        keyboard = []

        for character in characters:
            keyboard.append([InlineKeyboardButton(character.name, callback_data=character.name)])

        await update.effective_message.reply_text(message_str, reply_markup=InlineKeyboardMarkup(keyboard))

        return CHARACTER_SELECTION


async def character_selection_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character_name = query.data

    characters: List[Character] = context.user_data[CHARACTERS_CREATOR_KEY][CHARACTERS_KEY]
    character = next((character for character in characters if character.name == character_name), None)
    context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY] = character

    msg, reply_markup = create_main_menu_message(character)

    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_creation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    character = Character()
    context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY] = character

    await update.effective_message.reply_text(
        "Qual'è il nome del personaggio?\nRispondi a questo messaggio o premi /stop per terminare"
    )

    return NAME_SELECTION


async def character_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.effective_message.text

    # check if the character already exists
    if any(character.name == name for character in context.user_data[CHARACTERS_CREATOR_KEY].get(CHARACTERS_KEY, [])):
        await update.effective_message.reply_text("🔴 Esiste già un personaggio con lo stesso nome! 🔴\n"
            "Inserisci un altro nome o premi /stop per terminare"
        )
        return NAME_SELECTION

    character = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY]
    character.name = name

    await update.effective_message.reply_text(
        "Qual'è la razza del personaggio?\nRispondi a questo messaggio o premi /stop per terminare"
    )

    return RACE_SELECTION


async def character_race_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    race = update.effective_message.text

    character = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY]
    character.race = race

    await update.effective_message.reply_text(
        "Qual'è il genere del personaggio?\nRispondi a questo messaggio o premi /stop per terminare\n\n"
        "Esempio: Maschio"
    )

    return GENDER_SELECTION


async def character_gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    gender = update.effective_message.text

    character = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY]
    character.gender = gender

    await update.effective_message.reply_text(
        "Qual'è la classe del personaggio?\nRispondi a questo messaggio o premi /stop per terminare"
    )

    return CLASS_SELECTION


async def character_class_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    class_ = update.effective_message.text

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY]
    character.multi_class.add_class(class_)

    await update.effective_message.reply_text(
        "Quanti punti vita ha il tuo personaggio?\nRispondi a questo messaggio o premi /stop per terminare"
    )

    return HIT_POINTS_SELECTION


async def character_hit_points_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    hit_points = update.effective_message.text

    character = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY]
    character.hit_points = character.current_hit_points = int(hit_points)

    context.user_data[CHARACTERS_CREATOR_KEY][CHARACTERS_KEY] = []
    context.user_data[CHARACTERS_CREATOR_KEY][CHARACTERS_KEY].append(character)
    del context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY]
    context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY] = character

    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_bag_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    message_str, reply_markup = create_bag_menu(character)

    await send_and_save_message(
        update,
        context,
        message_str,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

    return BAG_MANAGEMENT


async def character_bag_new_object_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = (
        f"Rispondi con il nome dell'oggetto, quantità, descrizione e peso!\n\n"
        f"<b>Esempio:</b> <code>Pozione di guarigione superiore#2#Mi cura 8d4 + 8 di vita#1</code>\n"
        f"Il peso è opzionale!\n\n"
        f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione"
    )

    await query.edit_message_text(message_str, parse_mode=ParseMode.HTML)

    return BAG_ITEM_INSERTION


async def character_bag_item_insert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)
    item_info = update.effective_message.text
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)

    # Split the input, allowing up to 3 splits
    components = item_info.split('#', maxsplit=3)

    # Ensure there are either 3 or 4 components
    if len(components) < 3 or len(components) > 4:
        await send_and_save_message(
            update,
            context,
            "🔴 Formato errato! Assicurati di usare:\n"
            "nome#quantità#descrizione#(peso) 🔴"
        )
        return BAG_ITEM_INSERTION

    item_name, item_quantity, item_description = components[:3]
    item_weight = components[3] if len(components) == 4 else None

    # Validate item_quantity
    if not item_quantity.isdigit():
        await send_and_save_message(
            update,
            context,
            "🔴 La quantità deve essere un numero! 🔴"
        )
        return BAG_ITEM_INSERTION

    # Validate item_weight if provided
    if item_weight and not item_weight.isdigit():
        await send_and_save_message(
            update,
            context,
            "🔴 Il peso deve essere un numero se fornito! 🔴"
        )
        return BAG_ITEM_INSERTION

    # Convert quantity and weight to integers
    item_quantity = int(item_quantity)
    item_weight = int(item_weight) if item_weight else 0

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    # Check if there is enough space, considering item weight
    if item_weight > character.available_space():
        await send_and_save_message(
            update,
            context,
            "🔴 Ehy! Hai la borsa piena... eh vendi qualcosa! 🔴"
        )
    else:
        # Create the item and add it to the character's bag
        item = Item(item_name, item_description, item_quantity, item_weight)
        character.add_item(item)

        # Notify the user of success and available space
        available_space = character.available_space()
        success_message = (
            "Oggetto inserito con successo! ✅\n\n"
            f"{f'Puoi ancora trasportare {available_space} lb' if available_space > 0 else 'Psss... ora hai lo zaino pieno!'}"
        )
        await update.effective_message.reply_text(success_message)

    # Send the bag main menu
    message_str, reply_markup = create_bag_menu(character)
    await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return BAG_MANAGEMENT


async def character_bag_edit_object_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = (
        f"Rispondi con il nome dell'oggetto!\n"
        f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
        f"<b>Esempio:</b> <code>Pozione di guarigione superiore</code>\n"
    )

    await query.edit_message_text(message_str, parse_mode=ParseMode.HTML)

    return BAG_ITEM_EDIT


async def character_bag_item_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    item_name = update.effective_message.text
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    item: Item = next((item for item in character.bag if item_name == item.name), None)

    if not item:
        await send_and_save_message(
            update,
            context,
            "🔴 Oggetto non trovato! Prova di nuovo o usa /stop per terminare o un bottone del menù principale per cambiare funzione 🔴"
        )
        return BAG_ITEM_EDIT

    message_str, reply_markup = create_item_menu(item)

    # save the current item name
    context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ITEM_KEY] = item.name

    await send_and_save_message(update, context, message_str, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    return BAG_ITEM_EDIT


async def character_bag_item_delete_one_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    item_name = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ITEM_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.decrement_item_quantity(item_name)
    item: Item = next((item for item in character.bag if item_name == item.name), None)

    if item:
        await query.answer()
        message_str, reply_markup = create_item_menu(item)
        await query.edit_message_text(message_str, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return BAG_ITEM_EDIT
    else:
        await query.answer(f'{item_name} rimosso dalla borsa!', show_alert=True)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ITEM_KEY, None)
        message_str, reply_markup = create_bag_menu(character)
        await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

        return BAG_MANAGEMENT


async def character_bag_item_add_one_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    item_name = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ITEM_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.increment_item_quantity(item_name)
    item: Item = next((item for item in character.bag if item_name == item.name), None)

    message_str, reply_markup = create_item_menu(item)
    await query.edit_message_text(message_str, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    return BAG_ITEM_EDIT


async def character_bag_item_delete_all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    item_name = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ITEM_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    item: Item = next((item for item in character.bag if item_name == item.name), None)
    character.remove_item(item)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ITEM_KEY, None)

    message_str = "Oggetto rimosso con successo! ✅"
    await update.effective_message.reply_text(message_str)

    message_str, reply_markup = create_bag_menu(character)
    await update.effective_message.reply_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return BAG_MANAGEMENT


async def character_bag_ask_item_overwrite_quantity_query_handler(update: Update,
                                                                  context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "Inviami la quntità da sovrascrivere\n\nUsa /stop per terminare o un bottone del menù principale per cambiare funzione")

    return BAG_ITEM_OVERWRITE


async def character_ask_item_overwrite_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)

    try:
        item_quantity = int(text)
    except ValueError:
        await send_and_save_message(update, context, "La quantità inserita non è un numero!\n\n"
                                                     "Inserisci una quantità corretta o usa /stop per terminare "
                                                     "o un bottone del menù principale per cambiare funzione")
        return BAG_ITEM_OVERWRITE

    item_name = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ITEM_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    item: Item = next((item for item in character.bag if item_name == item.name), None)

    if item.quantity + item_quantity < 0:
        await send_and_save_message(update, context, f'Non hai almeno {item_quantity * -1} Pz di {item_name}')

    elif item_quantity < 0:

        character.decrement_item_quantity(item_name, item_quantity * -1)
        await send_and_save_message(update, context,
                                    f"{'Sono stati rimossi' if item_quantity > 1 else 'È stato rimosso'} "
                                    f"{item_quantity} Pz di {item_name} dal tuo inventario")
    elif item_quantity > 0:
        character.increment_item_quantity(item_name, item_quantity)
        await send_and_save_message(update, context,
                                    f"{'Sono stati aggiunti' if item_quantity > 1 else 'È stato aggiunto'} "
                                    f"{item_quantity} Pz di {item_name} al tuo inventario")
    else:
        await send_and_save_message(update, context, "🔴 La quantità inviata è uguale a quella presente!")

    message_str, reply_markup = create_item_menu(item)
    await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return BAG_ITEM_EDIT


async def character_spells_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    user_settings = context.user_data[CHARACTERS_CREATOR_KEY].get(USER_SETTINGS_KEY, {})
    spell_management_preference = user_settings.get('spell_management', 'paginate_by_level')

    if spell_management_preference == 'paginate_by_level':
        return await create_spell_levels_menu(character, update, context)
    else:
        return await create_spells_menu(character, update, context)


async def character_spells_by_level_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == SPELL_LEARN_CALLBACK_DATA:
        return await character_spell_new_query_handler(update, context)

    _, spell_level = data.split('|', maxsplit=1)
    spell_level = int(spell_level)

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    spells_of_selected_level = [spell for spell in character.spells if spell.level.value == spell_level]
    message_str = (f"Ecco la lista degli incantesimi di livello {spell_level}\n\n"
                   f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione")

    # Generates the keyboard for spells on the current page
    reply_markup = generate_spells_list_keyboard(spells_of_selected_level, draw_navigation_buttons=False)
    await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELLS_MENU


async def character_spells_menu_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    pages = context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY]
    current_page_index = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]

    if data == "prev_page":
        if current_page_index == 0:
            await query.answer("Sei alla prima pagina!", show_alert=True)
        else:
            context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] -= 1
            current_page_index -= 1
            # Refresh current page
            current_page = pages[current_page_index]
            level, spells_in_page = current_page
            message_str = ("Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n"
                           f"Ecco la lista degli incantesimi di livello {level}")
            reply_markup = generate_spells_list_keyboard(spells_in_page)
            await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return SPELLS_MENU

    elif data == "next_page":
        if current_page_index >= len(pages) - 1:
            await query.answer("Non ci sono altre pagine!", show_alert=True)
        else:
            context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] += 1
            current_page_index += 1  # Aggiorna l'indice locale
            # Aggiorna la pagina corrente
            current_page = pages[current_page_index]
            level, spells_in_page = current_page
            message_str = ("Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n"
                           f"Ecco la lista degli incantesimi di livello {level}")
            reply_markup = generate_spells_list_keyboard(spells_in_page)
            await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return SPELLS_MENU

    elif data == SPELL_LEARN_CALLBACK_DATA:

        await query.answer()
        return await character_spell_new_query_handler(update, context)

    elif data == SPELL_USAGE_BACK_MENU_CALLBACK_DATA:

        await query.answer()
        user_settings = context.user_data[CHARACTERS_CREATOR_KEY].get(USER_SETTINGS_KEY, {})
        spell_management_preference = user_settings.get('spell_management', 'paginate_by_level')
        character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
        if spell_management_preference == 'paginate_by_level':
            return await create_spell_levels_menu(character, update, context, edit_mode=True)
        else:
            return await create_spells_menu(character, update, context, edit_mode=True)

    else:
        await query.answer()
        _, spell_name = data.split('|', maxsplit=1)
        character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
        spell: Spell = next((spell for spell in character.spells if spell.name == spell_name), None)

        if spell is None:
            await query.answer("Incantesimo non trovato.", show_alert=True)
            return SPELLS_MENU

        message_str, reply_markup = create_spell_menu(spell)
        await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

        # Salva l'incantesimo corrente nei dati utente
        context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_SPELL_KEY] = spell

        return SPELL_VISUALIZATION


async def character_spell_visualization_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    if data == SPELL_EDIT_CALLBACK_DATA:

        await query.answer()
        await query.edit_message_text(
            "Inviami l'incantesimo inserendo il nome, descrizione e livello separati da un #\n\n"
            "<b>Esempio:</b> <code>Palla di fuoco#Unico incantesimo dei maghi#3</code>\n\n"
            "Usa /stop per terminare o un bottone del menù principale per cambiare funzione",
            parse_mode=ParseMode.HTML
        )

    elif data == SPELL_DELETE_CALLBACK_DATA:

        await query.answer()
        keyboard = [
            [
                InlineKeyboardButton("Si", callback_data='y'),
                InlineKeyboardButton("No", callback_data='n')
            ]
        ]
        await query.edit_message_text(
            "Sicuro di voler cancellare l'incantesimo\n\n"
            "Usa /stop per terminare o un bottone del menù principale per cambiare funzione?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == SPELL_BACK_MENU_CALLBACK_DATA:

        await query.answer()

        # Retrieve current pages and index
        pages = context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY]
        current_page_index = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]

        try:
            current_page = pages[current_page_index]
            level, spells_in_page = current_page
        except IndexError:
            await query.answer("Errore nel recuperare la pagina corrente.", show_alert=True)
            return SPELLS_MENU

        message_str = (
            "Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n"
            f"Ecco la lista degli incantesimi di livello {level}"
        )
        reply_markup = generate_spells_list_keyboard(spells_in_page, True)
        await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

        return SPELLS_MENU

    elif data == SPELL_USE_CALLBACK_DATA:

        await query.answer()
        spell: Spell = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_SPELL_KEY]
        character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

        # Generate inline keyboard with available spell slots
        message_str, reply_markup = create_spell_slots_menu_for_spell(character, spell)

        await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELL_ACTIONS


async def character_spell_new_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await send_and_save_message(
        update,
        context,
        "Inviami l'incantesimo inserendo il nome, descrizione e livello "
        "separati da un #\n\n"
        "<b>Esempio:</b> <code>Palla di fuoco#Unico incantesimo dei maghi#3</code>\n\n"
        "Usa /stop per terminare o un bottone del menù principale per cambiare funzione",
        parse_mode=ParseMode.HTML
    )

    return SPELL_LEARN


async def character_spell_learn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    spell_info = update.effective_message.text
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)

    try:
        spell_name, spell_desc, spell_level = spell_info.split("#", 2)
    except ValueError:
        await send_and_save_message(
            update,
            context,
            "🔴 Hai inserito i dati in un formato non valido!\n\n"
            "Invia di nuovo l'incantesimo o usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return SPELL_ACTIONS

    if spell_name.isdigit() or spell_desc.isdigit() or not spell_level.isdigit():
        await send_and_save_message(
            update,
            context,
            "🔴 Hai inserito i dati in un formato non valido!\n\n"
            "Invia di nuovo l'incantesimo o usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return SPELL_ACTIONS

    spell = Spell(spell_name, spell_desc, SpellLevel(int(spell_level)))
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    if any(spell_name == spell.name for spell in character.spells):
        await send_and_save_message(
            update,
            context,
            "🔴 Hai già appreso questa spell!\n\n"
            "Invia un altro incantesimo o usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return SPELL_ACTIONS

    if spell.level.value not in character.spell_slots.keys():
        await send_and_save_message(update,
                                    context,
                                    f"🔴 Questo incantesimo è di livello troppo alto!\n\n"
                                    f"Sblocca prima almeno uno slot di livello {spell.level.value} per impararlo.\n"
                                    f"Invia un altro incantesimo o usa /stop per terminare o un bottone del menù principale per cambiare funzione")
        return SPELL_ACTIONS

    character.learn_spell(spell)
    await send_and_save_message(update, context, "Incantesimo appreso con successo! ✅")

    return await create_spells_menu(character, update, context)


async def character_spell_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    spell_info = update.effective_message.text
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)

    try:
        spell_name, spell_desc, spell_level = spell_info.split("#", 2)
    except ValueError:
        await send_and_save_message(
            update,
            context,
            "🔴 Hai inserito i dati in un formato non valido!\n\n"
            "Invia di nuovo l'incantesimo o usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return SPELL_ACTIONS

    if spell_name.isdigit() or spell_desc.isdigit() or not spell_level.isdigit():
        await send_and_save_message(
            update,
            context,
            "🔴 Hai inserito i dati in un formato non valido!\n\n"
            "Invia di nuovo l'incantesimo o usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return SPELL_ACTIONS

    old_spell: Spell = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_SPELL_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    for spell in character.spells:
        if spell.name == old_spell.name:
            old_spell.name = spell_name
            old_spell.description = spell_desc
            old_spell.level = SpellLevel(int(spell_level))
            break

    await send_and_save_message(update, context, "Incantesimo modificato con successo!")

    return await create_spells_menu(character, update, context)


async def character_spell_delete_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    spell_to_forget: Spell = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_SPELL_KEY]

    if data == 'y':
        character.forget_spell(spell_to_forget.name)
    elif data == 'n':
        await send_and_save_message(
            update,
            context,
            f"Hai una buona memoria, ti ricordi ancora l'incantesimo {spell_to_forget.name}"
        )

    return await create_spells_menu(character, update, context)


async def character_spell_use_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    spell: Spell = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_SPELL_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    if data != SPELL_USAGE_BACK_MENU_CALLBACK_DATA:

        _, slot_level = data.split("|", maxsplit=1)

        try:
            character.use_spell(spell, int(slot_level))
        except ValueError as e:
            await query.answer(str(e), show_alert=True)
        else:
            await query.answer(f"Slot di livello {slot_level} usato", show_alert=True)

    else:
        await query.answer()

    message_str, reply_markup = create_spell_menu(spell)
    await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELL_VISUALIZATION


async def character_abilities_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    return await create_abilities_menu(character, update, context)


async def character_abilities_menu_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    if data == "prev_page":

        if context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] == 0:
            await query.answer("Sei alla prima pagina!", show_alert=True)
        else:
            context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] -= 1

        return ABILITIES_MENU

    elif data == "next_page":

        context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] += 1

    else:

        await query.answer()
        _, ability_name = data.split('|', maxsplit=1)
        character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
        ability: Ability = next((ability for ability in character.abilities if ability.name == ability_name), None)

        message_str, reply_markup = create_ability_menu(ability)
        await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

        # save the current ability in the userdata
        context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ABILITY_KEY] = ability

        return ABILITY_VISUALIZATION

    # retrieves other abilities
    try:
        ability_page = context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY][
            context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]
        ]
    except IndexError:
        await query.answer("Non ci sono altre pagine!", show_alert=True)
        context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] -= 1
        return ABILITIES_MENU

    message_str = ("Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n"
                   "Ecco la lista delle azioni")
    reply_markup = generate_abilities_list_keyboard(ability_page)
    await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def character_ability_visualization_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    if data == ABILITY_EDIT_CALLBACK_DATA:

        await query.answer()
        await query.edit_message_text("Inviami l'azione inserendo il nome, descrizione e livello separati da un #\n\n"
                                      "<b>Esempio:</b> <code>nome#bella descrizione#2</code>\n\n"
                                      "Usa /stop per terminare o un bottone del menù principale per cambiare funzione",
                                      parse_mode=ParseMode.HTML)

    elif data == ABILITY_DELETE_CALLBACK_DATA:

        await query.answer()
        keyboard = [
            [
                InlineKeyboardButton("Si", callback_data='y'),
                InlineKeyboardButton("No", callback_data='n')
            ]
        ]
        await query.edit_message_text("Sicuro di voler cancellare l'azione?\n\n"
                                      "Usa /stop per terminare o un bottone del menù principale per cambiare funzione",
                                      reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == ABILITY_BACK_MENU_CALLBACK_DATA:

        await query.answer()
        ability_page = context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY][
            context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]]

        message_str = ("Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
                       "Ecco la lista delle azione")
        reply_markup = generate_abilities_list_keyboard(ability_page)
        await query.edit_message_text(message_str, reply_markup=reply_markup)

        return ABILITIES_MENU

    elif data == ABILITY_USE_CALLBACK_DATA:

        character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
        ability: Ability = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ABILITY_KEY]

        if ability.uses == 0:
            await query.answer("Non hai più utilizzi per questa azione!", show_alert=True)
            return ABILITY_VISUALIZATION

        await query.answer()
        character.use_ability(ability)

        message_str, reply_keyboard = create_ability_menu(ability)
        await query.edit_message_text(message_str, reply_markup=reply_keyboard, parse_mode=ParseMode.HTML)

        return ABILITY_VISUALIZATION

    elif data == ABILITY_ACTIVE_CALLBACK_DATA:

        character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
        ability: Ability = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ABILITY_KEY]

        await query.answer()
        character.toggle_activate_ability(ability)

        message_str, reply_keyboard = create_ability_menu(ability)
        await query.edit_message_text(message_str, reply_markup=reply_keyboard, parse_mode=ParseMode.HTML)

        return ABILITY_VISUALIZATION

    return ABILITY_ACTIONS


async def character_ability_new_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "Inviami l'azione inserendo il nome, descrizione e numero utilizzi per tipo di riposo separati da un #\n\n"
        "<b>Esempio:</b> <code>nome#bella descrizione#2</code>\n\n"
        "Usa /stop per terminare o un bottone del menù principale per cambiare funzione",
        parse_mode=ParseMode.HTML
    )

    return ABILITY_LEARN


async def character_ability_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ability_info = update.effective_message.text
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)

    try:
        ability_name, ability_desc, ability_max_uses = ability_info.split("#", 2)
    except ValueError:
        await send_and_save_message(
            update,
            context,
            "🔴 Inserisci l'azione utilizzando il formato richiesto!\n\n"
            "Invia di nuovo l'azione o usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
            "<b>Esempio:</b> <code>nome#bella descrizione#2</code>",
            parse_mode=ParseMode.HTML
        )
        return ABILITY_LEARN

    if (not ability_name or ability_name.isdigit()
            or not ability_desc or ability_desc.isdigit()
            or not ability_max_uses or not ability_max_uses.isdigit()):
        await send_and_save_message(
            update,
            context,
            "🔴 Inserisci l'azione utilizzando il formato richiesto!\n\n"
            "Invia di nuovo l'azione o usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
            "<b>Esempio:</b> <code>nome#bella descrizione#2</code>",
            parse_mode=ParseMode.HTML
        )
        return ABILITY_LEARN

    # Ask for ability features
    features_chosen = {'is_passive': True, 'restoration_type': RestorationType.SHORT_REST}
    context.user_data[CHARACTERS_CREATOR_KEY][ABILITY_FEATURES_KEY] = features_chosen
    context.user_data[CHARACTERS_CREATOR_KEY][TEMP_ABILITY_KEY] = (ability_name, ability_desc, int(ability_max_uses))
    reply_markup = create_ability_keyboard(features_chosen)

    await send_and_save_message(
        update,
        context,
        "Scegli se l'azione è passiva o se si ricarica con un riposo lungo o corto\n"
        "Usa /stop per terminare o un bottone del menù principale per cambiare funzione", reply_markup=reply_markup
    )

    return ABILITY_LEARN


async def character_ability_features_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    feature, state = data.split('|', maxsplit=1)
    features_chosen = context.user_data[CHARACTERS_CREATOR_KEY][ABILITY_FEATURES_KEY]

    if feature == ABILITY_IS_PASSIVE_CALLBACK_DATA:
        features_chosen['is_passive'] = True if state == '1' else False
    elif feature == ABILITY_RESTORATION_TYPE_CALLBACK_DATA:
        features_chosen['restoration_type'] = RestorationType(state)

    reply_markup = create_ability_keyboard(features_chosen)
    context.user_data[CHARACTERS_CREATOR_KEY][ABILITY_FEATURES_KEY] = features_chosen
    await query.edit_message_reply_markup(reply_markup)

    return ABILITY_LEARN


async def character_ability_insert_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    ability_name, ability_desc, ability_max_uses = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_ABILITY_KEY]
    context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_ABILITY_KEY, None)
    features_chosen = context.user_data[CHARACTERS_CREATOR_KEY][ABILITY_FEATURES_KEY]

    ability = Ability(
        name=ability_name,
        description=ability_desc,
        is_passive=features_chosen['is_passive'],
        restoration_type=features_chosen['restoration_type'],
        max_uses=ability_max_uses,
        uses=ability_max_uses
    )
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    if any(ability_name == ability.name for ability in character.abilities):
        await send_and_save_message(
            update,
            context,
            "🔴 Hai già appreso questa azione!\n\n"
            "Invia un'altra azione o usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return ABILITY_LEARN

    character.learn_ability(ability)
    await send_and_save_message(update, context, "Azione appresa con successo! ✅")

    return await create_abilities_menu(character, update, context)


async def character_ability_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ability_info = update.effective_message.text
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)

    try:
        ability_name, ability_desc, ability_max_uses = ability_info.split("#", 2)
    except ValueError:
        await send_and_save_message(
            update,
            context,
            "🔴 Inserisci l'azione utilizzando il formato richiesto!\n\n"
            "Invia di nuovo l'azione o usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
            "<b>Esempio:</b> <code>nome#bella descrizione#2</code>",
            parse_mode=ParseMode.HTML
        )
        return ABILITY_ACTIONS

    if (not ability_name or ability_name.isdigit()
            or not ability_desc or ability_desc.isdigit()
            or not ability_max_uses or not ability_max_uses.isdigit()):
        await send_and_save_message(
            update,
            context,
            "🔴 Inserisci l'azione utilizzando il formato richiesto!\n\n"
            "Invia di nuovo l'azione o usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
            "<b>Esempio:</b> <code>nome#bella descrizione#2</code>",
            parse_mode=ParseMode.HTML
        )
        return ABILITY_ACTIONS

    old_ability: Ability = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ABILITY_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    for ability in character.abilities:
        if ability == old_ability:
            ability.name = ability_name
            ability.description = ability_desc
            ability.max_uses = int(ability_max_uses)
            break

    await send_and_save_message(update, context, "Azione modificata con successo!")

    return await create_abilities_menu(character, update, context)


async def character_ability_delete_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    ability_to_forget: Ability = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ABILITY_KEY]

    if data == 'y':
        character.forget_ability(ability_to_forget.name)
    elif data == 'n':
        await send_and_save_message(
            update,
            context,
            f"Hai una buona memoria, ti ricordi ancora l'azione {ability_to_forget.name}"
        )

    return await create_abilities_menu(character, update, context)


async def character_feature_point_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    message_str = (
        "<b>Gestione punti caratteristica</b>\n\n"
        "Inserisci i punti caratteristica come meglio desideri.\n\n"
        "Usa /stop per terminare o un bottone del menù principale per cambiare funzione"
    )
    await send_and_save_message(update, context, message_str, parse_mode=ParseMode.HTML)

    feature_points = character.feature_points.points

    messages = create_feature_points_messages(feature_points)
    for feature_point, message_data in messages.items():
        await send_and_save_message(
            update, context, message_data[0], reply_markup=message_data[1], parse_mode=ParseMode.HTML
        )

    return FEATURE_POINTS_EDIT


async def character_feature_points_edit_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    feature, action = query.data.split("|", maxsplit=1)

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    feature_points = character.feature_points.points

    # Update the feature point based on the action
    if action == "+":
        feature_points[feature] += 1
    elif action == "-" and feature_points[feature] > 0:
        feature_points[feature] -= 1
    else:
        await query.answer("Non puoi andare sotto lo zero", show_alert=True)
        return FEATURE_POINTS_EDIT

    character.change_feature_points(feature_points)

    # Update the message with the new feature points
    messagges: Dict[str, Tuple[str, InlineKeyboardMarkup]] = create_feature_points_messages(feature_points)

    text, keyboard = messagges[feature]
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await query.answer()

    return FEATURE_POINTS_EDIT


async def character_change_level_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    multi_class = character.multi_class

    if len(multi_class.classes) > 1:
        await query.answer()
        # If the character has more than one class, prompt the user to choose which class to level up/down
        buttons = [
            [InlineKeyboardButton(f"{class_name} (Livello {multi_class.get_class_level(class_name)})",
                                  callback_data=f"{data}|{class_name}")]
            for class_name in multi_class.classes.keys()
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        await send_and_save_message(
            update, context, "Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
                             "Scegli quale classe livellare in positivo o negativo:", reply_markup=keyboard
        )
    else:
        # If only one class, level up/down automatically
        class_name = next(iter(multi_class.classes))  # Get the only class name
        await apply_level_change(multi_class, class_name, data, query)
        msg, reply_markup = create_main_menu_message(character)
        await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_level_change_class_choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    action, class_name = data.split("|", maxsplit=1)

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    multi_class = character.multi_class

    # Apply the level change using the chosen class and action
    await apply_level_change(multi_class, class_name, action, query)
    msg, reply_markup = create_main_menu_message(character)
    await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def apply_level_change(multi_class: MultiClass, class_name: str, data: str, query: CallbackQuery) -> None:
    """Apply the level change to the selected class and update the user."""
    try:
        if data == LEVEL_UP_CALLBACK_DATA:
            multi_class.level_up(class_name)
        else:
            multi_class.level_down(class_name)

        await query.answer(f"{class_name} è ora di livello {multi_class.get_class_level(class_name)}!", show_alert=True)
    except ValueError as e:
        await query.answer(str(e), show_alert=True)


async def character_multiclassing_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    message_str = "<b>Gestione multi-classe</b>\n\n"
    keyboard = [[InlineKeyboardButton("Aggiungi classe", callback_data=MULTICLASSING_ADD_CALLBACK_DATA)]]

    if len(character.multi_class.classes) == 1:
        message_str += f"{character.name} non è un personaggio multi-classe."
    else:
        message_str += f"<code>{character.multi_class.list_classes()}</code>"
        keyboard.append(
            [InlineKeyboardButton("Rimuovi multi-classe", callback_data=MULTICLASSING_REMOVE_CALLBACK_DATA)])

    await send_and_save_message(
        update,
        context,
        message_str,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

    return MULTICLASSING_ACTIONS


async def character_multiclassing_add_class_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = (
        "Mandami il nome della classe da aggiungere e il livello separati da un #\n\n"
        "Esempio: <code>Guerriero#3</code>\n\n"
        "Usa /stop per terminare o un bottone del menù principale per cambiare funzione"
    )

    await send_and_save_message(update, context, message_str, parse_mode=ParseMode.HTML)

    return MULTICLASSING_ACTIONS


async def character_multiclassing_add_class_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    multi_class_info = update.effective_message.text
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)

    try:
        class_name, class_level = multi_class_info.split("#", maxsplit=1)
    except ValueError:
        await send_and_save_message(
            update,
            context,
            "🔴 Hai inviato il messaggio in un formato sbagliato!\n\n"
            "Invialo come classe#livello o usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return MULTICLASSING_ACTIONS

    if not class_name or class_name.isdigit() or not class_level or not class_level.isdigit():
        await send_and_save_message(
            update,
            context,
            "🔴 Hai inviato il messaggio in un formato sbagliato!\n\n"
            "Invialo come classe#livello o usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return MULTICLASSING_ACTIONS

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    try:
        character.add_class(class_name, int(class_level))
    except ValueError as e:
        await send_and_save_message(update, context, str(e), parse_mode=ParseMode.HTML)
        return MULTICLASSING_ACTIONS

    await send_and_save_message(
        update,
        context,
        "Classe inserita con successo! ✅\n\n"
        f"Complimenti adesso appartieni a {character.total_classes()} classi"
    )

    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_multiclassing_remove_class_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    keyboard = [
        [InlineKeyboardButton(class_name, callback_data=f"remove|{class_name}")]
        for class_name in character.multi_class.classes
    ]

    await send_and_save_message(
        update,
        context,
        "Che classe vuoi rimuovere?\n\n"
        "Usa /stop per terminare o un bottone del menù principale per cambiare funzione",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return MULTICLASSING_ACTIONS


async def character_multiclassing_remove_class_answer_query_handler(update: Update,
                                                                    context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    _, class_name = data.split("|", maxsplit=1)

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    multi_class = character.multi_class

    # Get the levels of the class to be removed
    removed_class_level = multi_class.get_class_level(class_name)

    # Remove the class from the multiclass
    multi_class.remove_class(class_name)

    # Check how many classes are left
    remaining_classes = list(multi_class.classes.keys())

    if len(remaining_classes) == 1:
        # If only one class is left, automatically assign the removed levels to it
        remaining_class_name = remaining_classes[0]
        multi_class.add_class(remaining_class_name, removed_class_level)

        # Send a confirmation message to the user
        await query.edit_message_text(
            f"La classe {class_name} è stata rimossa.\n"
            f"I {removed_class_level} livelli rimossi sono stati aggiunti alla classe {remaining_class_name}."
        )

        msg, reply_markup = create_main_menu_message(character)
        await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

        return FUNCTION_SELECTION

    else:
        # Store pending reassignment information in user_data
        context.user_data[CHARACTERS_CREATOR_KEY][PENDING_REASSIGNMENT] = {
            REMOVED_CLASS_LEVEL: removed_class_level,
            REMAINING_CLASSES: remaining_classes
        }

        # If more than one class remains, ask the user to select where to allocate the removed levels
        buttons = [
            [InlineKeyboardButton(f"{class_name} (Livello {multi_class.get_class_level(class_name)})",
                                  callback_data=f"assign_levels|{class_name}|{removed_class_level}")]
            for class_name in remaining_classes
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        # Send a message asking the user to select the class to assign the removed levels to
        await query.edit_message_text(
            f"La classe {class_name} è stata rimossa.\n"
            f"Seleziona una classe a cui assegnare i rimanenti {removed_class_level} livelli:",
            reply_markup=keyboard
        )

        return MULTICLASSING_ACTIONS


async def character_multiclassing_reassign_levels_query_handler(update: Update,
                                                                context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    _, class_name, removed_class_level = data.split("|", maxsplit=2)

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    try:
        character.add_class(class_name, int(removed_class_level))
    except ValueError as e:
        await send_and_save_message(update, context, str(e), parse_mode=ParseMode.HTML)
        return MULTICLASSING_ACTIONS

    # Clear pending reassignment since it has been handled
    context.user_data[CHARACTERS_CREATOR_KEY].pop(PENDING_REASSIGNMENT, None)

    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_deleting_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    keyboard = [
        [
            InlineKeyboardButton('Si', callback_data=AFFERMATIVE_CHARACTER_DELETION_CALLBACK_DATA),
            InlineKeyboardButton('No', callback_data=NEGATIVE_CHARACTER_DELETION_CALLBACK_DATA)
        ]
    ]

    message_str = (
        "Sei sicuro di voler cancellare il personaggio?\n\n"
        f"{character.name} - classe {', '.join(f'{class_name} (Livello {level})' for class_name, level in character.multi_class.classes.items())} "
        f"di L. {character.total_levels()}"
    )

    await send_and_save_message(update, context, message_str, reply_markup=InlineKeyboardMarkup(keyboard))

    return CHARACTER_DELETION


async def character_deleting_answer_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    current_character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    if data == AFFERMATIVE_CHARACTER_DELETION_CALLBACK_DATA:
        await query.answer()
        characters: List[Character] = context.user_data[CHARACTERS_CREATOR_KEY][CHARACTERS_KEY]

        # Remove the character from the list
        characters = [character for character in characters if character.name != current_character.name]
        context.user_data[CHARACTERS_CREATOR_KEY][CHARACTERS_KEY] = characters

        context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_CHARACTER_KEY, None)

        await update.effective_message.reply_text("Personaggio eliminato con successo ✅\n\n"
            "Usa il comando /start per avviare una nuova conversazione!\n"
            "Oppure invia direttamente i comandi /wiki o /character"
        )

        return ConversationHandler.END

    elif data == NEGATIVE_CHARACTER_DELETION_CALLBACK_DATA:
        await query.answer("Eliminazione personaggio annullata", show_alert=True)
        msg, reply_markup = create_main_menu_message(current_character)
        await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

        return FUNCTION_SELECTION


async def character_spells_slots_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    if character.spell_slots_mode is None:
        keyboard = [
            [
                InlineKeyboardButton("Automatica", callback_data=SPELL_SLOTS_AUTO_CALLBACK_DATA),
                InlineKeyboardButton("Manuale", callback_data=SPELL_SLOTS_MANUAL_CALLBACK_DATA),
            ]
        ]
        message_str = (
            "Che tipo di gestione vuoi scegliere per gli slot incantesimo?\n\n"
            "<b>Automatica:</b> scegli collegare il tuo personaggio ad una predefinita\n"
            "in questo modo quando sale di livello gli slot si modificano automaticamente.\n"
            "<b>N.B.</b> Questa gestione non considera il multi classing\n\n"
            "<b>Manuale:</b> Decidi tu quanti slot incantesimo avere e come gestirli"
        )
        await send_and_save_message(
            update, context, message_str, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
        )
    else:
        message_str, reply_markup = create_spell_slots_menu(context)
        await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELLS_SLOTS_MANAGEMENT


async def character_spells_slots_mode_answer_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    # Temporary check for automatic mode
    if data == SPELL_SLOTS_AUTO_CALLBACK_DATA:
        await query.answer("Modalità automatica ancora non gestita!", show_alert=True)
        return SPELLS_SLOTS_MANAGEMENT

    else:
        await query.answer()
        character.spell_slots_mode = SpellsSlotMode.MANUAL

        await send_and_save_message(
            update, context, "Modalità di gestione slot incantesimo impostata correttamente! ✅"
        )

        message_str, reply_markup = create_spell_slots_menu(context)
        await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

        return SPELLS_SLOTS_MANAGEMENT


async def character_spells_slots_add_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = ("Inserisci quanti slot inserire e di che livello in questo modo:\n\n"
                   "<code>numero slot#livello</code>\n\n"
                   "<b>Esempio:</b> 4#1 (4 slot di livello 1)\n\n"
                   "Usa /stop per terminare o un bottone del menù principale per cambiare funzione")

    await query.edit_message_text(message_str, parse_mode=ParseMode.HTML)

    return SPELL_SLOT_ADDING


async def character_spell_slot_add_answer_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = update.effective_message.text
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)

    try:
        slot_number, slot_level = data.split("#", maxsplit=1)
    except ValueError:
        await send_and_save_message(
            update,
            context,
            f"🔴 Formato sbagliato prova di nuovo!\n\nCorretto: 5#5 Usato: {data}\n\n"
            f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return SPELL_SLOT_ADDING

    if not slot_number or not slot_level or not slot_number.isdigit() or not slot_level.isdigit():
        await send_and_save_message(
            update,
            context,
            f"🔴 Formato sbagliato prova di nuovo!\n\nCorretto: 5#5 Usato: {data}\n\n"
            f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return SPELL_SLOT_ADDING

    if int(slot_level) > 9:
        await send_and_save_message(
            update, context, "🔴 Non puoi inserire uno slot di livello superiore al 9! 🔴\n\n"
                             "Usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return SPELL_SLOT_ADDING

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    if slot_level in character.spell_slots:
        await send_and_save_message(
            update, context, f"Slot di livello {slot_level} già presente, andrai a sostituire la quantità già esistente"
        )

    spell_slot = SpellSlot(int(slot_level), int(slot_number))
    character.add_spell_slot(spell_slot)

    await send_and_save_message(
        update, context, f"{slot_number} slot di livello {slot_level} aggiunti!"
    )

    message_str, reply_markup = create_spell_slots_menu(context)
    await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELLS_SLOTS_MANAGEMENT


async def character_spells_slots_remove_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = ("Inserisci quanti slot rimuovere e di che livello in questo modo:\n\n"
                   "<code>numero slot#livello</code>\n\n"
                   "<b>Esempio:</b> 4#1 (4 slot di livello 1)\n\n"
                   "Usa /stop per terminare o un bottone del menù principale per cambiare funzione")

    await query.edit_message_text(message_str, parse_mode=ParseMode.HTML)

    return SPELL_SLOT_REMOVING


async def character_spell_slot_remove_answer_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = update.effective_message.text
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)

    try:
        slot_number, slot_level = data.split("#", maxsplit=1)
    except ValueError:
        await send_and_save_message(
            update,
            context,
            f"🔴 Formato sbagliato prova di nuovo!\n\nCorretto: 5#5 Usato: {data}\n\n"
            f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return SPELL_SLOT_REMOVING

    if not slot_number or not slot_level or not slot_number.isdigit() or not slot_level.isdigit():
        await send_and_save_message(
            update,
            context,
            f"🔴 Formato sbagliato prova di nuovo!\n\nCorretto: 5#5 Usato: {data}\n\n"
            f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return SPELL_SLOT_REMOVING

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    slot_number = int(slot_number)
    slot_level = int(slot_level)

    if slot_level not in character.spell_slots:
        await send_and_save_message(
            update,
            context,
            f"Slot di livello {slot_level} non presente!\n\n"
            "Manda un nuovo messaggio con lo slot di livello corretto o Usa /stop per terminare o un bottone del menù principale per cambiare funzione"
        )
        return SPELL_SLOT_REMOVING

    spell_slot_to_edit = character.spell_slots[slot_level]

    if spell_slot_to_edit.total_slots - slot_number <= 0:
        await send_and_save_message(
            update,
            context,
            f"Il numero di slot da rimuovere copre o supera il numero di slot di livello {slot_level} già presenti.\n"
            f"Gli slot di questo livello sono stati tutti rimossi!"
        )
        character.spell_slots.pop(slot_level, None)
    else:
        spell_slot_to_edit.total_slots -= slot_number
        await send_and_save_message(update, context, f"{slot_number} slot di livello {slot_level} rimossi!")

    message_str, reply_markup = create_spell_slots_menu(context)
    await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELLS_SLOTS_MANAGEMENT


async def character_spells_slot_use_slot_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    _, slot_level = data.split("|", maxsplit=1)

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    try:
        character.use_spell_slot(int(slot_level))
        await query.answer()
    except ValueError as e:
        await query.answer(str(e), show_alert=True)

    message_str, reply_markup = create_spell_slots_menu(context)
    await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELLS_SLOTS_MANAGEMENT


async def character_spells_slot_use_reset_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.restore_all_spell_slots()
    await query.answer("Tutti gli spell slot sono stati ripristinati!", show_alert=True)

    message_str, reply_markup = create_spell_slots_menu(context)
    await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELLS_SLOTS_MANAGEMENT


async def character_spells_slot_change_mode_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Funzione ancora non gestita!", show_alert=True)

    return SPELLS_SLOTS_MANAGEMENT


async def character_damage_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await send_and_save_message(update, context, "Quanti danni hai subito?\n\n"
                                                 "Usa /stop per terminare o un bottone del menù principale per cambiare funzione")

    return DAMAGE_REGISTRATION


async def character_damage_registration_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)
    damage = update.effective_message.text

    if not damage or damage.isalpha():
        await send_and_save_message(update, context, "🔴 Inserisci un numero non una parola!\n\n"
                                                     "Usa /stop per terminare o un bottone del menù principale per cambiare funzione")
        return DAMAGE_REGISTRATION

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    # Fix retro-compatibility problem with the bug
    if isinstance(character.current_hit_points, str):
        character.current_hit_points = int(character.current_hit_points)

    character.current_hit_points -= int(damage)

    you_died_str = f"{damage} danni subiti!\n\n\n"
    character_died = False
    if character.current_hit_points <= -character.hit_points:
        you_died_str += create_skull_asciart()
        character_died = False

    await send_and_save_message(update, context, you_died_str, parse_mode=ParseMode.HTML)
    if character_died:
        await asyncio.sleep(3)

    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_healing_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await send_and_save_message(update, context, "Di quanto ti vuoi curare?\n\n"
                                                 "Usa /stop per terminare o un bottone del menù principale per cambiare funzione")

    return HEALING_REGISTRATION


async def character_healing_value_check_or_registration_handler(update: Update,
                                                                context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)
    healing = update.effective_message.text

    if not healing or not healing.isdigit():
        await send_and_save_message(update, context, "🔴 Inserisci un numero non una parola!\n\n"
                                                     "Usa /stop per terminare o un bottone del menù principale per cambiare funzione")
        return HEALING_REGISTRATION
    healing = int(healing)

    if healing <= 0:
        await send_and_save_message(update, context, "🔴 Inserisci un valore superiore a 0!\n\n"
                                                     "Usa /stop per terminare o un bottone del menù principale per cambiare funzione")
        return HEALING_REGISTRATION

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    if (character.current_hit_points + healing) > character.hit_points:
        keyboard = [
            [InlineKeyboardButton('Si', callback_data='y'), InlineKeyboardButton('No', callback_data='n')]
        ]
        await send_and_save_message(
            update,
            context,
            f"Se ti curi di {healing} punti ferita, aggiungerai "
            f"{(character.current_hit_points + healing) - character.hit_points} punti ferita temporanei.\n\n"
            "Vuoi aggiungere i punti ferita temporanei?\n\n"
            "Usa /stop per terminare o un bottone del menù principale per cambiare funzione",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        context.user_data[CHARACTERS_CREATOR_KEY][TEMP_HEALING_KEY] = healing
        return OVER_HEALING_CONFIRMATION

    # Fix retro-compatibility problem with the bug
    if isinstance(character.current_hit_points, str):
        character.current_hit_points = int(character.current_hit_points)
    character.current_hit_points += healing

    # flavour message
    message_str = ''
    if healing > 50:
        message_str = '<b>Diamine! Qualche divinità ti ha voluto proprio bene!</b>\n\n'

    message_str += f"Sei stato curato di {healing} PF!"
    await update.effective_message.reply_text(message_str, parse_mode=ParseMode.HTML)

    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_over_healing_registration_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    healing = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_HEALING_KEY]

    if data == 'y':

        character.current_hit_points += int(healing)
        await update.effective_message.reply_text(f"Sei stato curato di {healing} PF!\n"
                                                     f"{(character.current_hit_points + healing) - character.hit_points} punti ferita temporanei aggiunti!")

    elif data == 'n':
        character.current_hit_points = character.hit_points
        await update.effective_message.reply_text(f"Sei stato curato di {healing} PF!")

    context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_HEALING_KEY, None)
    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_hit_points_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    await send_and_save_message(
        update,
        context,
        f"Quanti sono ora i punti ferita di {character.name}?\n"
        f"N.B. I punti ferita attuali saranno ripristinati al massimo!\n\n"
        f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione"
    )

    return HIT_POINTS_REGISTRATION


async def character_hit_points_registration_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)
    hit_points = update.effective_message.text

    if not hit_points or hit_points.isalpha():
        await send_and_save_message(update, context, "🔴 Inserisci un numero non una parola!\n\n"
                                                     "Usa /stop per terminare o un bottone del menù principale per cambiare funzione")
        return HIT_POINTS_REGISTRATION

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    # Fix retro-compatibility problem with the bug
    if isinstance(character.current_hit_points, str):
        character.current_hit_points = int(character.current_hit_points)
    if isinstance(character.hit_points, str):
        character.hit_points = int(character.hit_points)

    character.hit_points = character.current_hit_points = int(hit_points)

    await update.effective_message.reply_text(f"Punti ferita aumentati a {hit_points}!")

    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_long_rest_warning_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = (
        "<b>Stai per effettuare un riposo lungo!</b>\n\n"
        "Questo comporta:\n"
        "- Ripristino dei punti ferita\n"
        "- Ripristino slot incantesimo\n\n"
        "Vuoi procedere? Usa /stop per terminare o un bottone del menù principale per cambiare funzione"
    )
    keyboard = [[InlineKeyboardButton("Riposa", callback_data=LONG_REST_CALLBACK_DATA)]]

    await send_and_save_message(update, context, message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                parse_mode=ParseMode.HTML)

    return LONG_REST


async def character_long_rest_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.long_rest()

    await query.answer("Riposo lungo effettuato!", show_alert=True)

    msg, reply_markup = create_main_menu_message(character)
    await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_short_rest_warning_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = (
        "<b>Stai per effettuare un riposo breve!</b>\n\n"
        "Questo comporta il ripristino di quelle azione che lo prevedono in caso di riposo breve.\n"
        "Per ora non ricarica gli slot incantesimo che prevedono di ricaricarsi con il riposo breve come quelli del Warlock.\n\n"
        "Vuoi procedere? Usa /stop per terminare o un bottone del menù principale per cambiare funzione"
    )
    keyboard = [[InlineKeyboardButton("Riposa", callback_data=SHORT_REST_CALLBACK_DATA)]]

    await send_and_save_message(update, context, message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                parse_mode=ParseMode.HTML)

    return SHORT_REST


async def character_short_rest_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.short_rest()

    await query.answer("Riposo breve effettuato!", show_alert=True)

    msg, reply_markup = create_main_menu_message(character)
    await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def send_dice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_edit: bool = True):
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    roll_history = character.get_rolls_history()
    message_str = (
        f"<b>Gestione tiri di dado</b>\n"
        "Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n"
        f"<code>{roll_history if roll_history != '' else 'Cronologia lanci vuota!\n\n'}</code>"
        "Seleziona quanti dadi vuoi tirare:\n\n"
    )

    if is_edit:
        starting_dice = context.user_data[CHARACTERS_CREATOR_KEY][DICE]
        reply_markup = create_dice_keyboard(starting_dice)
    else:
        starting_dice = STARTING_DICE.copy()
        reply_markup = create_dice_keyboard(starting_dice)
        context.user_data[CHARACTERS_CREATOR_KEY][DICE] = starting_dice

    if is_edit:
        message = await update.effective_message.edit_text(
            message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )
    else:
        message = await send_and_save_message(
            update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )

    context.user_data[CHARACTERS_CREATOR_KEY][DICE_MESSAGES] = message


async def delete_dice_menu(context: ContextTypes.DEFAULT_TYPE):
    message_to_delete = context.user_data[CHARACTERS_CREATOR_KEY][DICE_MESSAGES]
    await message_to_delete.delete()


async def dice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        query = update.callback_query
        await query.answer()

    await send_dice_menu(update, context, is_edit=False)

    return DICE_ACTION


async def dice_actions_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    temp_dice = context.user_data[CHARACTERS_CREATOR_KEY][DICE]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    if '|' in query.data:

        die, action = query.data.split('|', maxsplit=1)

        # update the dice number based on action
        if action == '+':
            temp_dice[die] += 1
        elif action == '-' and temp_dice[die] != 0:
            temp_dice[die] -= 1
        else:
            await query.answer("Non puoi tirare meno di un dado... genio", show_alert=True)
            return DICE_ACTION
        await query.answer()
        await send_dice_menu(update, context, is_edit=True)

    elif query.data == ROLL_DICE_CALLBACK_DATA:

        total_rolls = []

        for die, roll_to_do in temp_dice.items():
            if roll_to_do != 0:
                rolls = []

                for i in range(roll_to_do):
                    rolls.append(random.randint(1, ROLLS_MAP[die]))

                total_rolls.append((die, rolls))

        if not total_rolls:
            await query.answer("Non hai selezionato nemmeno un dado da rollare!", show_alert=True)
            return DICE_ACTION

        message_str = 'Roll eseguiti:\n'
        for die_name, die_rolls in total_rolls:
            message_str += f"{len(die_rolls)}{die_name}: [{', '.join([str(roll) for roll in die_rolls])}] = {sum(die_rolls)}\n"

        await query.answer(message_str, show_alert=True)

        # update history
        character.rolls_history.extend(total_rolls)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(DICE, None)
        await delete_dice_menu(context)
        await send_dice_menu(update, context, is_edit=True)

    elif query.data == ROLL_DICE_DELETE_HISTORY_CALLBACK_DATA:

        character.delete_rolls_history()
        await query.answer("Cronologia dadi cancellata!", show_alert=True)

        await send_dice_menu(update, context, is_edit=True)

    return DICE_ACTION


async def character_creator_notes_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    message_str, reply_markup = create_notes_menu(character)
    await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return NOTES_MANAGEMENT


async def character_creator_new_note_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = ("Inserisci la nota usando questo formato:\n"
                   "<code>Titolo#testo nota</code>\n\n"
                   "Il titolo della nota non è obbligatorio, puoi inserire anche solo il testo\n\n"
                   "Usa /stop per terminare o un bottone del menù principale per cambiare funzione")
    await query.edit_message_text(message_str, parse_mode=ParseMode.HTML)

    return NOTE_TEXT_ADD


async def character_creator_open_note_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    title_text = data.split('|')[1]

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    note_title, note_text = next(((title, text) for title, text in character.notes.items() if title == title_text))
    message_str = (f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
                   f"<b>{note_title}</b>\n\n"
                   f"<i>{note_text}</i>")

    keyboard = [
        [InlineKeyboardButton('Modifica nota', callback_data=f"{EDIT_NOTE_CALLBACK_DATA}|{note_title}")],
        [InlineKeyboardButton('Elimina nota', callback_data=f"{DELETE_NOTE_CALLBACK_DATA}|{note_title}")],
        [InlineKeyboardButton('Indietro 🔙', callback_data=f"{BACK_BUTTON_CALLBACK_DATA}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    # delete cached query data
    context.drop_callback_data(query)

    return NOTES_MANAGEMENT


async def character_creator_edit_note_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    title_text = data.split('|')[1]

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    note_title, note_text = next(((title, text) for title, text in character.notes.items() if title == title_text))

    message_str = (f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
                   f"Premi una volta sul titolo e sul testo della nota per copiarli:\n"
                   f"<code>{note_title}</code>\n\n"
                   f"<code>{note_text}</code>\n\n"
                   f"Inserisci la nota usando questo formato:\n"
                   f"<code>Titolo#testo nota</code>\n\n"
                   f"Il titolo della nota non è obbligatorio, puoi inserire anche solo il testo")

    await query.edit_message_text(message_str, parse_mode=ParseMode.HTML)

    return NOTE_TEXT_ADD


async def character_creator_delete_note_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    title_text = data.split('|')[1]

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.notes.pop(title_text, None)

    await query.answer('Nota eliminata con successo ✅', show_alert=True)
    message_str, reply_markup = create_notes_menu(character)
    await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return NOTES_MANAGEMENT


async def character_creator_notes_back_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    message_str, reply_markup = create_notes_menu(character)
    await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return NOTES_MANAGEMENT


async def character_creator_insert_note_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)
    text = update.effective_message.text
    message_splitted = text.split("#")

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    if len(message_splitted) == 1:
        note_title = extract_3_words(message_splitted[0])
        note_text = message_splitted[0]
    else:
        note_title = message_splitted[0]
        note_text = message_splitted[1]

    # manage insertion or edit
    if note_title in character.notes:
        character.notes.pop(note_title, None)
    character.notes[note_title] = note_text

    await send_and_save_message(update, context, "Nota salvata con successo! ✅")
    message_str, reply_markup = create_notes_menu(character)
    await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return NOTES_MANAGEMENT


async def character_creation_maps_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    message_str, reply_markup = create_maps_menu(character)

    await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return MAPS_MANAGEMENT


async def character_creation_show_maps_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    zone, maps_paths = query.data

    await send_and_save_message(update, context,
                                f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
                                f"Queste sono le mappe della zona {zone}")

    for path in maps_paths:
        keyboard = [
            [InlineKeyboardButton('Cancella', callback_data=f"{DELETE_SINGLE_MAP_CALLBACK_DATA}|{path}|{zone}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = await update.effective_message.reply_document(path, reply_markup=reply_markup)
        context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(message)

    message_str = "Scegli cosa vuoi fare"
    keyboard = [
        [InlineKeyboardButton('Aggiungi nuova mappa', callback_data=f"{ADD_NEW_MAP_CALLBACK_DATA}|{zone}")],
        [InlineKeyboardButton('Cancella tutte le mappe', callback_data=f"{DELETE_ALL_ZONE_MAPMS_CALLBACK_DATA}|{zone}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_and_save_message(update, context, message_str, reply_markup=reply_markup)


async def character_creator_delete_single_map_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    _, path, zone = data.split('|')
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.maps[zone].remove(path)

    await query.delete_message()

    return MAPS_MANAGEMENT


async def character_creator_add_map_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    _, zone = data.split('|')
    context.user_data[CHARACTERS_CREATOR_KEY][TEMP_ZONE_NAME] = zone

    message_str = (f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
                   f"Mandami la mappa come immagine o file")
    await send_and_save_message(update, context, message_str)

    context.user_data[CHARACTERS_CREATOR_KEY][ADD_OR_INSERT_MAPS] = 'add'

    return ADD_MAPS_FILES


async def character_creation_add_maps_done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)
    zone = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_ZONE_NAME]
    files_paths = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_MAPS_PATHS]

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.maps[zone].extend(files_paths)

    context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_ZONE_NAME, None)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_MAPS_PATHS, None)

    await send_and_save_message(update, context, "Mappe aggiunte con successo ✅")
    message_str, reply_markup = create_maps_menu(character)
    await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return MAPS_MANAGEMENT


async def character_creation_maps_delete_all_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    _, zone = data.split('|')
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.maps.pop(zone, None)

    await send_and_save_message(update, context, f"Le mappe della zona {zone} sono state cancellate con successo ✅")
    message_str, reply_markup = create_maps_menu(character)
    await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def character_creation_new_maps_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = (f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
                   f"Inviami il nome della zona rappresentata dalle mappe")
    await query.edit_message_text(message_str)

    context.user_data[CHARACTERS_CREATOR_KEY][ADD_OR_INSERT_MAPS] = 'insert'

    return MAPS_ZONE


async def character_creation_ask_maps_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(message)
    text = message.text
    context.user_data[CHARACTERS_CREATOR_KEY][TEMP_ZONE_NAME] = text

    message_str = (f"Usa /stop per terminare o un bottone del menù principale per cambiare funzione\n\n"
                   f"Mandami la mappa come immagine o file")
    await send_and_save_message(update, context, message_str)

    return MAPS_FILES


async def store_map_file_or_photo(file: File, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # create the folder for the file
    os.makedirs(MAPS_DIR_PATH, exist_ok=True)
    # Download the file on the disk
    file_name = file.file_path.split('/')[-1].split('.')[0]
    file_ext = file.file_path.split('/')[-1].split('.')[1]
    final_file_path = await file.download_to_drive(f"{MAPS_DIR_PATH}/{file_name}.{file_ext}")
    # save the file path in a temp location
    if TEMP_MAPS_PATHS not in context.user_data[CHARACTERS_CREATOR_KEY]:
        context.user_data[CHARACTERS_CREATOR_KEY][TEMP_MAPS_PATHS] = []

    context.user_data[CHARACTERS_CREATOR_KEY][TEMP_MAPS_PATHS].append(str(final_file_path))

    message_str = (f"Invia un altro file o foto oppure usa il comando /done per terminare\n\n"
                   f"Puoi sempre usare il comando /stop per terminare la conversazione oppure premere su un pulsante "
                   f"del menu principale")
    await send_and_save_message(update, context, message_str)

    if context.user_data[CHARACTERS_CREATOR_KEY][ADD_OR_INSERT_MAPS] == 'insert':
        return MAPS_FILES
    else:
        return ADD_MAPS_FILES


async def character_creation_store_map_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(message)
    document = await message.effective_attachment.get_file()

    if document.file_size > FileSizeLimit.FILESIZE_DOWNLOAD:
        await send_and_save_message(update, context, "Il file inviato è troppo grande!\n"
                                                     "La dimensione massima è di 20MB")
        return MAPS_FILES

    return await store_map_file_or_photo(document, update, context)


async def character_creation_store_map_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(message)
    photo = await message.effective_attachment[-1].get_file()

    return await store_map_file_or_photo(photo, update, context)


async def character_creation_maps_done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].append(update.effective_message)
    zone = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_ZONE_NAME]
    files_paths = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_MAPS_PATHS]

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.maps[zone] = files_paths

    context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_ZONE_NAME, None)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_MAPS_PATHS, None)

    await send_and_save_message(update, context, "Mappe salvate con successo!")
    message_str, reply_markup = create_maps_menu(character)
    await send_and_save_message(update, context, message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return MAPS_MANAGEMENT


async def character_creator_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    # Inizializza le impostazioni utente se non presenti
    if USER_SETTINGS_KEY not in context.user_data[CHARACTERS_CREATOR_KEY]:
        context.user_data[CHARACTERS_CREATOR_KEY][USER_SETTINGS_KEY] = {}

    user_settings = context.user_data[CHARACTERS_CREATOR_KEY][USER_SETTINGS_KEY]

    # Genera il messaggio e la tastiera per le impostazioni
    message_text, keyboard = generate_settings_menu_single_message(user_settings)

    # Invia il messaggio con il menu delle impostazioni
    await send_and_save_message(
        update,
        context,
        message_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

    return SETTINGS_MENU_STATE


async def character_creator_settings_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    # Formato atteso: 'setting|key|value'
    if data.startswith('setting|'):
        _, setting_key, selected_value = data.split('|')

        # Aggiorna le impostazioni dell'utente
        if USER_SETTINGS_KEY not in context.user_data:
            context.user_data[CHARACTERS_CREATOR_KEY][USER_SETTINGS_KEY] = {}
        context.user_data[CHARACTERS_CREATOR_KEY][USER_SETTINGS_KEY][setting_key] = selected_value

        # Rispondi alla query
        await query.answer()

        # Rigenera il messaggio e la tastiera delle impostazioni
        user_settings = context.user_data[CHARACTERS_CREATOR_KEY][USER_SETTINGS_KEY]
        message_text, keyboard = generate_settings_menu_single_message(user_settings)

        # Modifica il messaggio originale utilizzando query.edit_message_text
        try:
            await query.edit_message_text(
                text=message_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        except telegram.error.BadRequest as e:
            # Gestisci errori nell'editing del messaggio
            print(f"Errore nell'editing del messaggio: {e}")
            await query.answer('Non è stato possibile aggiornare le impostazioni.', show_alert=True)

        # Ritorna allo stato del menu delle impostazioni
        return SETTINGS_MENU_STATE

    else:
        # Gestisci callback data non riconosciuti
        await query.answer('Opzione non riconosciuta.', show_alert=True)
        return SETTINGS_MENU_STATE


async def character_generic_main_menu_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await check_pending_reassignment_for_multiclassing(update, context)

    MAINMENU_CALLBACKDATA_TO_CALLBACK = {
        r"^level_(up|down)$": character_change_level_query_handler,
        fr"^{LEVEL_UP_CALLBACK_DATA}\|.*$|^{LEVEL_DOWN_CALLBACK_DATA}\|.*$": character_level_change_class_choice_handler,
        fr"^{BAG_CALLBACK_DATA}$": character_bag_query_handler,
        fr"^{SPELLS_CALLBACK_DATA}$": character_spells_query_handler,
        fr"^{ABILITIES_CALLBACK_DATA}$": character_abilities_query_handler,
        fr"^{SPELLS_SLOT_CALLBACK_DATA}$": character_spells_slots_query_handler,
        fr"^{FEATURE_POINTS_CALLBACK_DATA}$": character_feature_point_query_handler,
        fr"^{MULTICLASSING_CALLBACK_DATA}$": character_multiclassing_query_handler,
        fr"^{DELETE_CHARACTER_CALLBACK_DATA}$": character_deleting_query_handler,
        fr"^{DAMAGE_CALLBACK_DATA}$": character_damage_query_handler,
        fr"^{HEALING_CALLBACK_DATA}$": character_healing_query_handler,
        fr"^{HIT_POINTS_CALLBACK_DATA}$": character_hit_points_query_handler,
        fr"^{LONG_REST_WARNING_CALLBACK_DATA}$": character_long_rest_warning_query_handler,
        fr"^{SHORT_REST_WARNING_CALLBACK_DATA}$": character_short_rest_warning_query_handler,
        fr"^{ROLL_DICE_MENU_CALLBACK_DATA}$": dice_handler,
        fr"^{SETTINGS_CALLBACK_DATA}$": character_creator_settings,
        fr"^{MAPS_CALLBACK_DATA}$": character_creation_maps_query_handler,
        fr"^{NOTES_CALLBACK_DATA}$": character_creator_notes_query_handler
    }

    for regex, func in MAINMENU_CALLBACKDATA_TO_CALLBACK.items():
        if re.match(regex, query.data):
            messages = context.user_data[CHARACTERS_CREATOR_KEY].get(LAST_MENU_MESSAGES, [])
            for message in messages:
                try:
                    await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
                except TelegramError as e:
                    logger.warning(f"Errore durante la cancellazione del messaggio: {e}")
            context.user_data[CHARACTERS_CREATOR_KEY][LAST_MENU_MESSAGES].clear()
            return await func(update, context)


async def check_pending_reassignment_for_multiclassing(update, context):
    # Rollback for multiclass management
    if PENDING_REASSIGNMENT in context.user_data[CHARACTERS_CREATOR_KEY]:
        # Get the pending reassignment information
        pending_reassignment = context.user_data[CHARACTERS_CREATOR_KEY][PENDING_REASSIGNMENT]
        removed_class_level = pending_reassignment[REMOVED_CLASS_LEVEL]
        remaining_classes = pending_reassignment[REMAINING_CLASSES]

        if len(remaining_classes) == 1:
            # Automatically reassign levels if only one class is left
            remaining_class_name = remaining_classes[0]
            character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
            multi_class = character.multi_class

            multi_class.add_class(remaining_class_name, removed_class_level)

            await update.message.reply_text(f"Il comando /stop è stato ricevuto.\n"
                                            f"I {removed_class_level} livelli rimossi sono stati aggiunti automaticamente alla classe {remaining_class_name}.")
        else:
            # Ask the user to finish reassigning the levels before stopping
            await update.message.reply_text("Devi assegnare i livelli rimanenti prima di poter usare il comando /stop.")
            return MULTICLASSING_ACTIONS

    else:

        context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_CHARACTER_KEY, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ITEM_KEY, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(PENDING_REASSIGNMENT, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(ABILITY_FEATURES_KEY, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_ABILITY_KEY, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ABILITY_KEY, None)
