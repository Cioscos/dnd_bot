import logging
import random
from typing import List, Tuple, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes, ConversationHandler

from src.model.character_creator.Ability import Ability, RestorationType
from src.model.character_creator.Character import Character, SpellsSlotMode
from src.model.character_creator.Item import Item
from src.model.character_creator.MultiClass import MultiClass
from src.model.character_creator.Spell import Spell, SpellLevel
from src.model.character_creator.SpellSlot import SpellSlot
from src.util import chunk_list, generate_abilities_list_keyboard, generate_spells_list_keyboard

logger = logging.getLogger(__name__)

CHARACTER_CREATOR_VERSION = "1.0.0"

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
 FEATURE_POINTS_EDIT,
 ABILITIES_MENU,
 ABILITY_VISUALIZATION,
 ABILITY_ACTIONS,
 ABILITY_LEARN,
 SPELLS_MENU,
 SPELL_VISUALIZATION,
 SPELL_ACTIONS,
 SPELL_LEARN,
 MULTICLASSING_ACTIONS,
 SPELLS_SLOTS_MANAGEMENT,
 SPELL_SLOT_ADDING,
 SPELL_SLOT_REMOVING,
 DAMAGE_REGISTRATION,
 HEALING_REGISTRATION,
 HIT_POINTS_REGISTRATION,
 LONG_REST,
 SHORT_REST,
 DICE_ACTION) = map(int, range(14, 45))

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
CURRENT_SPELL_KEY = 'current_spell'
# Keys to store the data allowing a rollback in the case user use /stop command before ending the multiclass deleting
PENDING_REASSIGNMENT = 'pending_reassignment'
REMOVED_CLASS_LEVEL = 'removed_class_level'
REMAINING_CLASSES = 'remaining_classes'
# spell slots
SPELL_SLOTS = 'spell_slots'
DICE = 'dice'
DICE_MESSAGES = 'dice_messages'
ACTIVE_CONV = 'active_conv'

# character main menu callback keys
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
ABILITY_BACK_MENU_CALLBACK_DATA = "ability_back_menu"
ABILITY_IS_PASSIVE_CALLBACK_DATA = "ability_is_passive"
ABILITY_RESTORATION_TYPE_CALLBACK_DATA = "ability_restoration_type"
ABILITY_INSERT_CALLBACK_DATA = "ability_insert"
SPELL_LEARN_CALLBACK_DATA = "spells_learn"
SPELL_EDIT_CALLBACK_DATA = "spell_edit"
SPELL_DELETE_CALLBACK_DATA = "spell_delete"
SPELL_BACK_MENU_CALLBACK_DATA = "spell_back_menu"
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


def create_main_menu_message(character: Character) -> Tuple[str, InlineKeyboardMarkup]:
    message_str = (f"Benvenuto nella gestione personaggio! v.{CHARACTER_CREATOR_VERSION}\n"
                   f"<b>Nome personaggio:</b> {character.name} L. {character.total_levels()}\n"
                   f"<b>Razza:</b> {character.race}\n"
                   f"<b>Genere:</b> {character.gender}\n"
                   f"<b>Classe:</b> {', '.join(f"{class_name} (Level {level})" for class_name, level in character.multi_class.classes.items())}\n\n"
                   f"<b>Punti ferita:</b> {character.current_hit_points}/{character.hit_points} PF\n"
                   f"<b>Slot incantesimo</b>\n{"\n".join([f"L{str(slot.level)} {"🟦" * (slot.total_slots - slot.used_slots)}{"🟥" * slot.used_slots}" for slot in character.spell_slots.values()]) if character.spell_slots else "Non hai registrato ancora nessuno Slot incantesimo"}")

    message_str += (f"\n<b>Punti caratteristica</b>\n{str(character.feature_points)}\n\n"
                    f"<b>Peso trasportato:</b> {character.encumbrance} Lb")

    keyboard = [
        [
            InlineKeyboardButton('Level down', callback_data=LEVEL_DOWN_CALLBACK_DATA),
            InlineKeyboardButton('Level up', callback_data=LEVEL_UP_CALLBACK_DATA)
        ],
        [
            InlineKeyboardButton('Prendi danni', callback_data=DAMAGE_CALLBACK_DATA),
            InlineKeyboardButton('Curati', callback_data=HEALING_CALLBACK_DATA)
        ],
        [
            InlineKeyboardButton('Punti ferita', callback_data=HIT_POINTS_CALLBACK_DATA)
        ],
        [
            InlineKeyboardButton('Borsa', callback_data=BAG_CALLBACK_DATA),
            InlineKeyboardButton('Abilità', callback_data=ABILITIES_CALLBACK_DATA),
            InlineKeyboardButton('Spell', callback_data=SPELLS_CALLBACK_DATA)
        ],
        [InlineKeyboardButton('Gestisci slot incantesimo', callback_data=SPELLS_SLOT_CALLBACK_DATA)],
        [InlineKeyboardButton('Punti caratteristica', callback_data=FEATURE_POINTS_CALLBACK_DATA)],
        [InlineKeyboardButton('Gestisci multiclasse', callback_data=MULTICLASSING_CALLBACK_DATA)],
        [
            InlineKeyboardButton('Riposo lungo', callback_data=LONG_REST_WARNING_CALLBACK_DATA),
            InlineKeyboardButton('Riposo breve', callback_data=SHORT_REST_WARNING_CALLBACK_DATA)
        ],
        [InlineKeyboardButton('Lancia Dado', callback_data=ROLL_DICE_MENU_CALLBACK_DATA)],
        [InlineKeyboardButton('Elimina personaggio', callback_data=DELETE_CHARACTER_CALLBACK_DATA)]
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
            f"Forza {feature_points['strength']}",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("-", callback_data="strength|-"),
                    InlineKeyboardButton("+", callback_data="strength|+")
                ]
            ])
        ),
        'dexterity': (
            f"Destrezza {feature_points['dexterity']}",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("-", callback_data="dexterity|-"),
                    InlineKeyboardButton("+", callback_data="dexterity|+")
                ]
            ])
        ),
        'constitution': (
            f"Costituzione {feature_points['constitution']}",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("-", callback_data="constitution|-"),
                    InlineKeyboardButton("+", callback_data="constitution|+")
                ]
            ])
        ),
        'intelligence': (
            f"Intelligenza {feature_points['intelligence']}",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("-", callback_data="intelligence|-"),
                    InlineKeyboardButton("+", callback_data="intelligence|+")
                ]
            ])
        ),
        'wisdom': (
            f"Saggezza {feature_points['wisdom']}",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("-", callback_data="wisdom|-"),
                    InlineKeyboardButton("+", callback_data="wisdom|+")
                ]
            ])
        ),
        'charisma': (
            f"Carisma {feature_points['charisma']}",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("-", callback_data="charisma|-"),
                    InlineKeyboardButton("+", callback_data="charisma|+")
                ]
            ])
        )
    }


def create_spells_slot_menu(context: ContextTypes.DEFAULT_TYPE):
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    message_str = f"Seleziona i pulsanti nella prima linea per utilizzare uno slot del livello corrispondente.\n\n"
    keyboard = []
    if not character.spell_slots:

        message_str += "Non hai ancora nessuno slot incantesimo"

    else:

        spell_slots_buttons = []
        for slot in character.spell_slots.values():
            spell_slots_buttons.append(InlineKeyboardButton(
                f"{str(slot.level)} {"🟦" * (slot.total_slots - slot.used_slots)}{"🟥" * slot.used_slots}",
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


def create_bag_menu(character: Character) -> Tuple[str, InlineKeyboardMarkup]:
    message_str = (f"<b>Oggetti nella borsa</b>\n\n"
                   f"{'\n'.join(f'<code>{item.name}</code> x{item.quantity}' for item in character.bag) if character.bag else
                   "Lo zaino è ancora vuoto"}")

    keyboard = [[InlineKeyboardButton('Inserisci nuovo oggetto', callback_data=BAG_ITEM_INSERTION_CALLBACK_DATA)]]

    if character.bag:
        keyboard.append([InlineKeyboardButton('Modifica oggetto', callback_data=BAG_ITEM_EDIT)])

    return message_str, InlineKeyboardMarkup(keyboard)


def create_item_menu(item: Item) -> Tuple[str, InlineKeyboardMarkup]:
    message_str = (f"<b>{item.name:<{50}}</b>{item.quantity}Pz\n\n"
                   f"<b>Descrizione</b>\n{item.description}\n\n"
                   f"Premi /stop per terminare\n\n")

    keyboard = [
        [
            InlineKeyboardButton("-", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|-"),
            InlineKeyboardButton("+", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|+")
        ],
        [InlineKeyboardButton("Rimuovi tutti", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|all")]
    ]

    return message_str, InlineKeyboardMarkup(keyboard)


async def create_spells_menu(character: Character, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_str = f"<b>Gestione spells</b>\n\n"
    if not character.spells:

        message_str += "Non conosci ancora nessuna spell ‍🤷‍♂️"
        keyboard = [
            [InlineKeyboardButton("Impara nuova spell", callback_data=SPELL_LEARN_CALLBACK_DATA)]
        ]
        await update.effective_message.reply_text(message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                                  parse_mode=ParseMode.HTML)

        return SPELL_LEARN

    else:

        message_str += ("Usa /stop per tornare al menu\n"
                        "Ecco la lista delle abilità")

    spells = character.spells
    spells_pages = chunk_list(spells, 8)

    context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY] = spells_pages
    context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] = 0
    current_page = spells_pages[context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]]

    reply_markup = generate_spells_list_keyboard(current_page)
    await update.effective_message.reply_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return SPELLS_MENU


async def create_abilities_menu(character: Character, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_str = f"<b>Gestione abilità</b>\n\n"
    if not character.abilities:

        message_str += "Non hai ancora nessuna abilità 🤷‍♂️"
        keyboard = [
            [InlineKeyboardButton("Impara nuova abilità", callback_data=ABILITY_LEARN_CALLBACK_DATA)]
        ]
        await update.effective_message.reply_text(message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                                  parse_mode=ParseMode.HTML)

        return ABILITY_LEARN

    else:
        message_str += ("Usa /stop per tornare al menu\n"
                        "Ecco la lista delle abilità")

    abilities = character.abilities
    abilities_pages = chunk_list(abilities, 8)

    context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY] = abilities_pages
    context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] = 0
    current_page = abilities_pages[context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]]

    reply_markup = generate_abilities_list_keyboard(current_page)

    await update.effective_message.reply_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return ABILITIES_MENU


def create_ability_menu(ability: Ability) -> Tuple[str, InlineKeyboardMarkup]:
    message_str = (f"<b>{ability.name}</b>\n\n"
                   f"<b>Descrizione</b>\n{ability.description}\n\n"
                   f"<b>Usi</b> {ability.uses}x\n\n"
                   f"<i>Abilità {'passiva' if ability.is_passive else 'attiva'}, si ricarica con un riposo "
                   f"{'breve' if ability.restoration_type == RestorationType.SHORT_REST else 'lungo'}</i>")
    keyboard = [
        [
            InlineKeyboardButton("Modifica", callback_data=ABILITY_EDIT_CALLBACK_DATA),
            InlineKeyboardButton("Dimentica", callback_data=ABILITY_DELETE_CALLBACK_DATA)
        ],
        [InlineKeyboardButton('Usa', callback_data=ABILITY_USE_CALLBACK_DATA)],
        [InlineKeyboardButton("Indietro 🔙", callback_data=ABILITY_BACK_MENU_CALLBACK_DATA)]
    ]

    return message_str, InlineKeyboardMarkup(keyboard)


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

            await update.message.reply_text(f"Il comando /stop è stato ricevuto.\n"
                                            f"I {removed_class_level} livelli rimossi sono stati aggiunti automaticamente alla classe {remaining_class_name}.")
        else:
            # Ask the user to finish reassigning the levels before stopping
            await update.message.reply_text("Devi assegnare i livelli rimanenti prima di poter usare il comando /stop.")
            return MULTICLASSING_ACTIONS

    else:

        if CURRENT_CHARACTER_KEY in context.user_data[CHARACTERS_CREATOR_KEY]:
            character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
            msg, reply_markup = create_main_menu_message(character)
            await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

        else:
            await update.effective_message.reply_text('Ok! Usa il comando /start per avviare una nuova conversazione!\n'
                                                      'Oppure invia direttamente i comandi /wiki o /character')

            return ConversationHandler.END

        context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_CHARACTER_KEY, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ITEM_KEY, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(PENDING_REASSIGNMENT, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(ABILITY_FEATURES_KEY, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_ABILITY_KEY, None)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ABILITY_KEY, None)

        return FUNCTION_SELECTION


async def character_creation_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text('Ok! Usa il comando /start per avviare una nuova conversazione!\n'
                                              'Oppure invia direttamente i comandi /wiki o /character')

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
        await update.message.reply_text("Usare /stop per uscire dalla wiki prima di usare la gestione dei personaggi.")
        return ConversationHandler.END

    context.user_data[ACTIVE_CONV] = 'character'

    # Check for BOT_DATA_CHAT_IDS initialization
    if BOT_DATA_CHAT_IDS not in context.bot_data or update.effective_chat.id not in context.bot_data.get(
            BOT_DATA_CHAT_IDS, []):
        await update.effective_message.reply_text(
            "La prima volta devi interagire con il bot usando il comando /start")
        return ConversationHandler.END

    # check if the function is called in a group or not
    if update.effective_chat.type != ChatType.PRIVATE:
        await update.effective_message.reply_text(
            "La funzione di gestione del personaggio può essere usata solo in privato!\n"
            "Ritorno al menù principale...")
        return ConversationHandler.END

    message_str = f"Benvenuto nella gestione del personaggio!\n"

    # check if the user has the character creator DB
    if CHARACTERS_CREATOR_KEY not in context.user_data:
        context.user_data[CHARACTERS_CREATOR_KEY] = {}

    # check if the user has already some characters created
    if CHARACTERS_KEY not in context.user_data[CHARACTERS_CREATOR_KEY] or not context.user_data[CHARACTERS_CREATOR_KEY][
        CHARACTERS_KEY]:
        message_str += (f"{update.effective_user.name} sembra che non hai inserito ancora nessun personaggio!\n"
                        f"Usa il comando /newCharacter per crearne uno nuovo o /stop per terminare la conversazione.")

        await update.effective_message.reply_text(message_str)
        return CHARACTER_CREATION

    else:
        characters: List[Character] = context.user_data[CHARACTERS_CREATOR_KEY][CHARACTERS_KEY]
        message_str += "Seleziona uno dei personaggi da gestire o creane no nuovo con /newCharacter:"
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
    # create a character oject and save it temporarly in the user date
    character = Character()
    context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY] = character

    await update.effective_message.reply_text(
        "Qual'è il nome del personaggio?\nRispondi a questo messaggio o premi /stop per terminare")

    return NAME_SELECTION


async def character_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.effective_message.text

    # check if the character already exists
    if any(character.name == name for character in context.user_data[CHARACTERS_CREATOR_KEY].get(CHARACTERS_KEY, [])):
        await update.effective_message.reply_text("🔴 Esiste già un personaggio con lo stesso nome! 🔴\n"
                                                  "Inserisci un altro nome o premi /stop per terminare")

        return NAME_SELECTION

    character = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY]
    character.name = name

    await update.effective_message.reply_text(
        "Qual'è la razza del personaggio?\nRispondi a questo messaggio o premi /stop per terminare")

    return RACE_SELECTION


async def character_race_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    race = update.effective_message.text

    character = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY]
    character.race = race

    await update.effective_message.reply_text(
        "Qual'è il genere del personaggio?\nRispondi a questo messaggio o premi /stop per terminare\n\n"
        "Esempio: Maschio")

    return GENDER_SELECTION


async def character_gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    gender = update.effective_message.text

    character = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY]
    character.gender = gender

    await update.effective_message.reply_text(
        "Qual'è la classe del personaggio?\nRispondi a questo messaggio o premi /stop per terminare")

    return CLASS_SELECTION


async def character_class_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    class_ = update.effective_message.text

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY]
    character.multi_class.add_class(class_)

    await update.effective_message.reply_text(
        "Quanti punti vita ha il tuo personaggio?\nRispondi a questo messaggio o premi /stop per terminare")

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

    await update.effective_message.reply_text(
        message_str,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

    return BAG_MANAGEMENT


async def character_bag_new_object_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = (f"Rispondi con il nome dell'oggetto, quantità, descrizione e peso!\n\n"
                   f"<b>Esempio:</b> <code>Pozione di guarigione superiore#2#Mi cura 8d4 + 8 di vita#1</code>\n"
                   f"Il peso è opzionale!\n"
                   f"Premi /stop per terminare")

    await query.edit_message_text(message_str, parse_mode=ParseMode.HTML)

    return BAG_ITEM_INSERTION


async def character_bag_item_insert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    item_info = update.effective_message.text

    # Split the input, allowing up to 3 splits
    components = item_info.split('#', maxsplit=3)

    # Ensure there are either 3 or 4 components
    if len(components) < 3 or len(components) > 4:
        await update.effective_message.reply_text(
            "🔴 Formato errato! Assicurati di usare:\n"
            "nome#quantità#descrizione#(peso) 🔴"
        )
        return BAG_ITEM_INSERTION

    item_name, item_quantity, item_description = components[:3]
    item_weight = components[3] if len(components) == 4 else None

    # Validate item_quantity
    if not item_quantity.isdigit():
        await update.effective_message.reply_text(
            "🔴 La quantità deve essere un numero! 🔴"
        )
        return BAG_ITEM_INSERTION

    # Validate item_weight if provided
    if item_weight and not item_weight.isdigit():
        await update.effective_message.reply_text(
            "🔴 Il peso deve essere un numero se fornito! 🔴"
        )
        return BAG_ITEM_INSERTION

    # Convert quantity and weight to integers
    item_quantity = int(item_quantity)
    item_weight = int(item_weight) if item_weight else 0

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    # Check if there is enough space, considering item weight
    if item_weight > character.available_space():

        await update.effective_message.reply_text("🔴 Ehy! Hai la borsa piena... eh vendi qualcosa! 🔴")

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

    # send the bag main menu
    message_str, reply_markup = create_bag_menu(character)
    await update.effective_message.reply_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return BAG_MANAGEMENT


async def character_bag_edit_object_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = (f"Rispondi con il nome dell'oggetto!\n"
                   f"Premi /stop per terminare\n\n"
                   f"<b>Esempio:</b> <code>Pozione di guarigione superiore</code>\n")

    await update.effective_message.reply_text(message_str, parse_mode=ParseMode.HTML)

    return BAG_ITEM_EDIT


async def character_bag_item_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    item_name = update.effective_message.text

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    item: Item = next((item for item in character.bag if item_name == item.name), None)

    if not item:
        await update.effective_message.reply_text("🔴 Oggetto non trovato! Prova di nuovo o premi /stop 🔴")
        return BAG_ITEM_EDIT

    message_str, reply_markup = create_item_menu(item)

    # save the current item name
    context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ITEM_KEY] = item.name

    await update.effective_message.reply_text(message_str, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
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
        await update.effective_message.reply_text(message_str, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return BAG_ITEM_EDIT

    else:

        await query.answer(f'{item_name} rimosso dalla borsa!', show_alert=True)
        context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ITEM_KEY, None)
        message_str, reply_markup = create_bag_menu(character)
        await update.effective_message.reply_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

        return BAG_MANAGEMENT


async def character_bag_item_add_one_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    item_name = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ITEM_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.increment_item_quantity(item_name)
    item: Item = next((item for item in character.bag if item_name == item.name), None)

    message_str, reply_markup = create_item_menu(item)
    await update.effective_message.reply_text(message_str, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    return BAG_ITEM_EDIT


async def character_bag_item_delete_all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    item_name = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ITEM_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    item: Item = next((item for item in character.bag if item_name == item.name), None)
    character.remove_item(item)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ITEM_KEY, None)

    message_str = f"Oggetto rimosso con successo! ✅"
    await update.effective_message.reply_text(message_str, parse_mode=ParseMode.HTML)

    message_str, reply_markup = create_bag_menu(character)
    await update.effective_message.reply_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return BAG_MANAGEMENT


async def character_spells_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    return await create_spells_menu(character, update, context)


async def character_spells_menu_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    if data == "prev_page":

        if context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] == 0:
            await query.answer("Sei alla prima pagina!", show_alert=True)
        else:
            context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] -= 1

        return SPELLS_MENU

    elif data == "next_page":

        context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] += 1

    elif data == SPELL_LEARN_CALLBACK_DATA:

        return await character_spell_new_query_handler(update, context)

    else:

        await query.answer()
        character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
        spell: Spell = next((spell for spell in character.spells if spell.name == data), None)
        message_str = (f"<b>{spell.name:<{50}}</b>L{spell.level.value}\n\n"
                       f"<b>Descrizione</b>\n{spell.description}")
        keyboard = [
            [
                InlineKeyboardButton("Modifica", callback_data=SPELL_EDIT_CALLBACK_DATA),
                InlineKeyboardButton("Dimentica", callback_data=SPELL_DELETE_CALLBACK_DATA)
            ],
            [InlineKeyboardButton("Indietro 🔙", callback_data=SPELL_BACK_MENU_CALLBACK_DATA)]
        ]
        await query.edit_message_text(message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                      parse_mode=ParseMode.HTML)

        # save the current ability in the userdata
        context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_SPELL_KEY] = spell

        return SPELL_VISUALIZATION

    # retrieves other spells
    try:
        spells_page = context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY][
            context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]
        ]
    except IndexError:
        await query.answer("Non ci sono altre pagine!", show_alert=True)
        context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY] -= 1
        return SPELLS_MENU

    message_str = ("Usa /stop per tornare al menu\n"
                   "Ecco la lista degli incantesimi")
    reply_markup = generate_spells_list_keyboard(spells_page)
    await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def character_spell_visualization_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == SPELL_EDIT_CALLBACK_DATA:

        await query.edit_message_text("Inviami l'incantesimo inserendo il nome, descrizione e livello "
                                      "separati da un #\n\n"
                                      "<b>Esempio:</b> <code>Palla di fuoco#Unico incantesimo dei maghi#3</code>\n\n",
                                      parse_mode=ParseMode.HTML)

    elif data == SPELL_DELETE_CALLBACK_DATA:

        keyboard = [
            [
                InlineKeyboardButton("Si", callback_data='y'),
                InlineKeyboardButton("No", callback_data='n')
            ]
        ]
        await query.edit_message_text("Sicuro di voler cancellare l'incantesimo?",
                                      reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == SPELL_BACK_MENU_CALLBACK_DATA:

        spells_page = context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY][
            context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]]

        message_str = ("Usa /stop per tornare al menu\n"
                       "Ecco la lista degli incantesimi")
        reply_markup = generate_spells_list_keyboard(spells_page)
        await query.edit_message_text(message_str, reply_markup=reply_markup)

        return SPELLS_MENU

    return SPELL_ACTIONS


async def character_spell_new_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await update.effective_message.reply_text("Inviami l'incantesimo inserendo il nome, descrizione e livello "
                                              "separati da un #\n\n"
                                              "<b>Esempio:</b> <code>Palla di fuoco#Unico incantesimo dei maghi#3</code>\n\n",
                                              parse_mode=ParseMode.HTML)

    return SPELL_LEARN


async def character_spell_learn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    spell_info = update.effective_message.text

    try:
        spell_name, spell_desc, spell_level = spell_info.split("#", 2)
    except ValueError:
        await update.effective_message.reply_text("🔴 Hai inserito i dati in un formato non valido!\n\n"
                                                  "Invia di nuovo l'incantesimo o usa /stop per terminare")
        return SPELL_ACTIONS

    if spell_name.isdigit() or spell_desc.isdigit() or not spell_level.isdigit():
        await update.effective_message.reply_text("🔴 Hai inserito i dati in un formato non valido!\n\n"
                                                  "Invia di nuovo l'incantesimo o usa /stop per terminare")
        return SPELL_ACTIONS

    spell = Spell(spell_name, spell_desc, SpellLevel(int(spell_level)))
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    if any(spell_name == spell.name for spell in character.spells):
        await update.effective_message.reply_text("🔴 Hai già appreso questa spell!\n\n"
                                                  "Invia un altro incantesimo o usa /stop per terminare")
        return SPELL_ACTIONS

    character.learn_spell(spell)
    await update.effective_message.reply_text("Incantesimo appresa con successo! ✅")

    return await create_spells_menu(character, update, context)


async def character_spell_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    spell_info = update.effective_message.text

    try:
        spell_name, spell_desc, spell_level = spell_info.split("#", 2)
    except ValueError:
        await update.effective_message.reply_text("🔴 Hai inserito i dati in un formato non valido!\n\n"
                                                  "Invia di nuovo l'incantesimo o usa /stop per terminare")
        return SPELL_ACTIONS

    if spell_name.isdigit() or spell_desc.isdigit() or not spell_level.isdigit():
        await update.effective_message.reply_text("🔴 Hai inserito i dati in un formato non valido!\n\n"
                                                  "Invia di nuovo l'incantesimo o usa /stop per terminare")
        return SPELL_ACTIONS

    old_spell: Spell = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_SPELL_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    for spell in character.spells:
        if spell.name == old_spell.name:
            old_spell.name = spell_name
            old_spell.description = spell_desc
            old_spell.level = SpellLevel(int(spell_level))
            break

    await update.effective_message.reply_text("Incantesimo modificato con successo!")

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
        await update.effective_message.reply_text(f"Hai una buona memoria, ti ricordi ancora l'incantesimo "
                                                  f"{spell_to_forget.name}")

    return await create_spells_menu(character, update, context)


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
        character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
        ability: Ability = next((ability for ability in character.abilities if ability.name == data), None)

        message_str, reply_keyboard = create_ability_menu(ability)
        await query.edit_message_text(message_str, reply_markup=reply_keyboard, parse_mode=ParseMode.HTML)

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

    message_str = ("Usa /stop per tornare al menu\n"
                   "Ecco la lista delle abilità")
    reply_markup = generate_abilities_list_keyboard(ability_page)
    await query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def character_ability_visualization_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    if data == ABILITY_EDIT_CALLBACK_DATA:

        await query.answer()
        await query.edit_message_text("Inviami l'abilità inserendo il nome e la descrizione separate da un #\n\n"
                                      "<b>Esempio:</b> <code>nome#bella descrizione</code>\n\n",
                                      parse_mode=ParseMode.HTML)

    elif data == ABILITY_DELETE_CALLBACK_DATA:

        await query.answer()
        keyboard = [
            [
                InlineKeyboardButton("Si", callback_data='y'),
                InlineKeyboardButton("No", callback_data='n')
            ]
        ]
        await query.edit_message_text("Sicuro di voler cancellare l'abilità?",
                                      reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == ABILITY_BACK_MENU_CALLBACK_DATA:

        await query.answer()
        ability_page = context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY][
            context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]]

        message_str = ("Usa /stop per tornare al menu\n"
                       "Ecco la lista delle abilità")
        reply_markup = generate_abilities_list_keyboard(ability_page)
        await query.edit_message_text(message_str, reply_markup=reply_markup)

        return ABILITIES_MENU

    elif data == ABILITY_USE_CALLBACK_DATA:

        character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
        ability: Ability = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ABILITY_KEY]

        if ability.uses == 0:
            await query.answer("Non hai più utilizzi per questa abilità!", show_alert=True)
            return ABILITY_VISUALIZATION

        await query.answer()
        character.use_ability(ability)

        message_str, reply_keyboard = create_ability_menu(ability)
        await query.edit_message_text(message_str, reply_markup=reply_keyboard, parse_mode=ParseMode.HTML)

        return ABILITY_VISUALIZATION

    return ABILITY_ACTIONS


async def character_ability_new_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "Inviami l'abilità inserendo il nome, descrizione e numero utilizzi per tipo di riposo separati da un #\n\n"
        "<b>Esempio:</b> <code>nome#bella descrizione#2</code>",
        parse_mode=ParseMode.HTML
    )

    return ABILITY_LEARN


async def character_ability_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ability_info = update.effective_message.text

    try:
        ability_name, ability_desc, ability_max_uses = ability_info.split("#", 2)
    except ValueError:
        await update.effective_message.reply_text("🔴 Inserisci l'abilità utilizzando il formato richiesto!\n\n"
                                                  "Invia di nuovo l'abilità o usa /stop per terminare\n\n"
                                                  "<b>Esempio:</b> <code>nome#bella descrizione#2</code>",
                                                  parse_mode=ParseMode.HTML)
        return ABILITY_LEARN

    if (not ability_name or ability_name.isdigit()
            or not ability_desc or ability_desc.isdigit()
            or not ability_max_uses or not ability_max_uses.isdigit()):
        await update.effective_message.reply_text("🔴 Inserisci l'abilità utilizzando il formato richiesto!\n\n"
                                                  "Invia di nuovo l'abilità o usa /stop per terminare\n\n"
                                                  "<b>Esempio:</b> <code>nome#bella descrizione#2</code>",
                                                  parse_mode=ParseMode.HTML)
        return ABILITY_LEARN

    # Ask for ability features
    features_chosen = {'is_passive': True, 'restoration_type': 'short'}
    context.user_data[CHARACTERS_CREATOR_KEY][ABILITY_FEATURES_KEY] = features_chosen
    context.user_data[CHARACTERS_CREATOR_KEY][TEMP_ABILITY_KEY] = (ability_name, ability_desc, int(ability_max_uses))
    reply_markup = create_ability_keyboard(features_chosen)

    await update.effective_message.reply_text(
        "Scegli se l'abilità è passiva o se si ricarica con un riposo lungo o corto\n"
        "Usa /stop per terminare", reply_markup=reply_markup)

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
        await update.effective_message.reply_text("🔴 Hai già appreso questa abilità!\n\n"
                                                  "Invia un'altra abilità o usa /stop per terminare")
        return ABILITY_LEARN

    character.learn_ability(ability)
    await update.effective_message.reply_text("Abilità appresa con successo! ✅")

    return await create_abilities_menu(character, update, context)


async def character_ability_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ability_info = update.effective_message.text

    try:
        ability_name, ability_desc, ability_max_uses = ability_info.split("#", 2)
    except ValueError:
        await update.effective_message.reply_text("🔴 Inserisci l'abilità utilizzando il formato richiesto!\n\n"
                                                  "Invia di nuovo l'abilità o usa /stop per terminare\n\n"
                                                  "<b>Esempio:</b> <code>nome#bella descrizione#2</code>",
                                                  parse_mode=ParseMode.HTML)
        return ABILITY_ACTIONS

    if (not ability_name or ability_name.isdigit()
            or not ability_desc or ability_desc.isdigit()
            or not ability_max_uses or not ability_max_uses.isdigit()):
        await update.effective_message.reply_text("🔴 Inserisci l'abilità utilizzando il formato richiesto!\n\n"
                                                  "Invia di nuovo l'abilità o usa /stop per terminare\n\n"
                                                  "<b>Esempio:</b> <code>nome#bella descrizione#2</code>",
                                                  parse_mode=ParseMode.HTML)
        return ABILITY_ACTIONS

    old_ability: Ability = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ABILITY_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    for ability in character.abilities:
        if ability == old_ability:
            ability.name = ability_name
            ability.description = ability_desc
            ability.max_uses = int(ability_max_uses)
            break

    await update.effective_message.reply_text("Abilità modificata con successo!")

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
        await update.effective_message.reply_text(f"Hai una buona memoria, ti ricordi ancora l'abilità "
                                                  f"{ability_to_forget.name}")

    return await create_abilities_menu(character, update, context)


async def character_feature_point_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    message_str = (f"<b>Gestione punti caratteristica</b>\n\n"
                   f"Inserisci i punti caratteristica come meglio desideri.\n"
                   f"Usa /stop per terminare")
    await update.effective_message.reply_text(message_str, parse_mode=ParseMode.HTML)

    feature_points = character.feature_points.points

    messagges = create_feature_points_messages(feature_points)
    for feature_point, message_data in messagges.items():
        await update.effective_message.reply_text(message_data[0], reply_markup=message_data[1],
                                                  parse_mode=ParseMode.HTML)

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
        await update.effective_message.reply_text("Scegli quale classe livellare in positivo o negativo:",
                                                  reply_markup=keyboard)
    else:
        # If only one class, level up/down automatically
        class_name = next(iter(multi_class.classes))  # Get the only class name
        await apply_level_change(multi_class, class_name, data, query)
        msg, reply_markup = create_main_menu_message(character)
        await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

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
    keyboard = [
        [InlineKeyboardButton("Aggiungi classe", callback_data=MULTICLASSING_ADD_CALLBACK_DATA)]
    ]

    if len(character.multi_class.classes) == 1:

        message_str += f"{character.name} non è un personaggio multi-classe"

    else:

        message_str += f"<code>{character.multi_class.list_classes()}</code>"
        keyboard.append(
            [InlineKeyboardButton("Rimuovi multi-classe", callback_data=MULTICLASSING_REMOVE_CALLBACK_DATA)])

    await update.effective_message.reply_text(message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                              parse_mode=ParseMode.HTML)

    return MULTICLASSING_ACTIONS


async def character_multiclassing_add_class_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await update.effective_message.reply_text("Mandami il nome della classe da aggiungere e il livello separati "
                                              "da un #\n\n"
                                              "Esempio: <code>Guerriero#3</code>", parse_mode=ParseMode.HTML)

    return MULTICLASSING_ACTIONS


async def character_multiclassing_add_class_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    multi_class_info = update.effective_message.text

    try:
        class_name, class_level = multi_class_info.split("#", maxsplit=1)
    except ValueError:
        await update.effective_message.reply_text("🔴 Hai inviato il messaggio in un formato sbagliato!\n\n"
                                                  "Invialo come classe#livello")
        return MULTICLASSING_ACTIONS

    if not class_name or class_name.isdigit() or not class_level or not class_level.isdigit():
        await update.effective_message.reply_text("🔴 Hai inviato il messaggio in un formato sbagliato!\n\n"
                                                  "Invialo come classe#livello")
        return MULTICLASSING_ACTIONS

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    try:
        character.add_class(class_name, int(class_level))
    except ValueError as e:
        await update.effective_message.reply_text(str(e), parse_mode=ParseMode.HTML)
        return MULTICLASSING_ACTIONS

    await update.effective_message.reply_text("Classe inserita con successo! ✅\n\n"
                                              f"Complimenti adesso appartieni a {character.total_classes()} classi")

    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_multiclassing_remove_class_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    keyboard = []

    for class_name in character.multi_class.classes:
        keyboard.append([InlineKeyboardButton(class_name, callback_data=f"remove|{class_name}")])

    await update.effective_message.reply_text("Che classe vuoi rimuovere?",
                                              reply_markup=InlineKeyboardMarkup(keyboard))

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
        await query.edit_message_text(f"La classe {class_name} è stata rimossa.\n"
                                      f"I {removed_class_level} livelli rimossi sono stati aggiunti alla classe {remaining_class_name}.")

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
        await query.edit_message_text(f"La classe {class_name} è stata rimossa.\n"
                                      f"Seleziona una classe a cui assegnare i rimanenti {removed_class_level} livelli:",
                                      reply_markup=keyboard)

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
        await update.effective_message.reply_text(str(e), parse_mode=ParseMode.HTML)
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

    await query.edit_message_text("Sei sicuro di voler chancellare il personaggio?\n\n"
                                              f"{character.name} - classe {', '.join(f"{class_name} (Level {level})" for class_name, level in character.multi_class.classes.items())} di L. {character.total_levels()}",
                                              reply_markup=InlineKeyboardMarkup(keyboard))

    return CHARACTER_DELETION


async def character_deleting_answer_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    current_character: Character = context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_CHARACTER_KEY, None)

    if data == AFFERMATIVE_CHARACTER_DELETION_CALLBACK_DATA:

        await query.answer()
        characters: List[Character] = context.user_data[CHARACTERS_CREATOR_KEY][CHARACTERS_KEY]

        for character in characters:
            if character.name == current_character.name:
                characters.remove(character)

        await update.effective_message.reply_text("Personaggio eliminato con successo ✅\n\n"
                                                  "Usa il comando /start per avviare una nuova conversazione!\n"
                                                  "Oppure invia direttamente i comandi /wiki o /character")

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
        await update.effective_message.reply_text(
            "Che tipo di gestione vuoi scegliere per gli slot incantesimo?\n\n"
            "<b>Automatica:</b> scegli collegare il tuo personaggio ad una predefinita\n"
            "in questo modo quando sale di livello gli slot si modificano "
            "automaticamente.\n"
            "<b>N.B.</b>Questa gestione non considera il multi classing\n\n"
            "<b>Manuale:</b> Decidi tu quanti slot incantesimo avere e come gestirli",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    else:

        message_str, reply_markup = create_spells_slot_menu(context)
        await update.effective_message.reply_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELLS_SLOTS_MANAGEMENT


async def character_spells_slots_mode_answer_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    # Temporary check
    # Automatic management is still something not managed
    if data == SPELL_SLOTS_AUTO_CALLBACK_DATA:

        await query.answer("Modalità automatica ancora non gestita!", show_alert=True)
        return SPELLS_SLOTS_MANAGEMENT

    else:

        await query.answer()
        character.spell_slots_mode = SpellsSlotMode.MANUAL

        await update.effective_message.reply_text("Modalità di gestione slot incantesimo impostata correttamente! ✅")

        msg, reply_markup = create_main_menu_message(character)
        await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

        return FUNCTION_SELECTION


async def character_spells_slots_add_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = ("Inserisci quanti slot inserire e di che livello in questo modo:\n\n"
                   "<code>numero slot#livello</code>\n\n"
                   "<b>Esempio:</b> 4#1 (4 slot di livello 1)")

    await update.callback_query.edit_message_text(message_str, parse_mode=ParseMode.HTML)

    return SPELL_SLOT_ADDING


async def character_spell_slot_add_answer_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = update.effective_message.text

    try:
        slot_number, slot_level = data.split("#", maxsplit=1)
    except ValueError:
        await update.effective_message.reply_text("🔴 Formato sbagliato prova di nuovo!\n\n"
                                                  f"Corretto: 5#5 Usato: {data}")
        return SPELL_SLOT_ADDING

    if not slot_number or not slot_level or not slot_number.isdigit() or not slot_level.isdigit():
        await update.effective_message.reply_text("🔴 Formato sbagliato prova di nuovo!\n\n"
                                                  f"Corretto: 5#5 Usato: {data}")
        return SPELL_SLOT_ADDING

    if int(slot_number) > 9:
        await update.effective_message.reply_text("🔴 Non puoi inserire uno slot di livello superiore al 9! 🔴")
        return SPELL_SLOT_ADDING

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    if slot_level in character.spell_slots:
        await update.effective_message.reply_text(f"Slot di livello {slot_level} già presente, andrai a sostituire")

    spell_slot = SpellSlot(int(slot_level), int(slot_number))
    character.add_spell_slot(spell_slot)

    await update.effective_message.reply_text(f"{slot_number} slot di livello {slot_level} aggiunti!")

    message_str, reply_markup = create_spells_slot_menu(context)
    await update.effective_message.reply_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELLS_SLOTS_MANAGEMENT


async def character_spells_slots_remove_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = ("Inserisci quanti slot rimuovere e di che livello in questo modo:\n\n"
                   "<code>numero slot#livello</code>\n\n"
                   "<b>Esempio:</b> 4#1 (4 slot di livello 1)")

    await update.callback_query.edit_message_text(message_str, parse_mode=ParseMode.HTML)

    return SPELL_SLOT_REMOVING


async def character_spell_slot_remove_answer_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = update.effective_message.text

    try:
        slot_number, slot_level = data.split("#", maxsplit=1)
    except ValueError:
        await update.effective_message.reply_text("🔴 Formato sbagliato prova di nuovo!\n\n"
                                                  f"Corretto: 5#5 Usato: {data}")
        return SPELL_SLOT_REMOVING

    if not slot_number or not slot_level or not slot_number.isdigit() or not slot_level.isdigit():
        await update.effective_message.reply_text("🔴 Formato sbagliato prova di nuovo!\n\n"
                                                  f"Corretto: 5#5 Usato: {data}")
        return SPELL_SLOT_REMOVING

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    if slot_level not in character.spell_slots:
        await update.effective_message.reply_text(f"Slot di livello {slot_level} non presente!\n\n"
                                                  f"Manda un nuovo messaggio con lo slot di livello corretto o annulla con /stop")

        return SPELL_SLOT_REMOVING

    spell_slot_to_edit = character.spell_slots[int(slot_level)]

    if spell_slot_to_edit.total_slots - int(slot_number) <= 0:

        await update.effective_message.reply_text("Il numero di slot da rimuovere coprono o superano "
                                                  f"il numero di slot di livello {slot_level} già presenti.\n"
                                                  f"Gli slot di questo livello sono stati tutti rimossi!")

        character.spell_slots.pop(int(slot_level), None)

    else:

        spell_slot_to_edit.total_slots -= int(slot_number)
        await update.effective_message.reply_text(f"{slot_number} slot di livello {slot_level} rimossi!")

    message_str, reply_markup = create_spells_slot_menu(context)
    await update.effective_message.reply_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

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

    message_str, reply_markup = create_spells_slot_menu(context)
    await update.callback_query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELLS_SLOTS_MANAGEMENT


async def character_spells_slot_use_reset_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.restore_all_spell_slots()
    await query.answer("Tutti gli spell slot sono stati ripristinati!", show_alert=True)

    message_str, reply_markup = create_spells_slot_menu(context)
    await update.callback_query.edit_message_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELLS_SLOTS_MANAGEMENT


async def character_spells_slot_change_mode_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Funzione ancora non gestita!", show_alert=True)

    return SPELLS_SLOTS_MANAGEMENT


async def character_damage_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await update.effective_message.reply_text("Quanti danni hai subito?")

    return DAMAGE_REGISTRATION


async def character_damage_registration_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    damage = update.effective_message.text

    if not damage or damage.isalpha():
        await update.effective_message.reply_text("🔴 Inserisci un numero non una parola!")
        return DAMAGE_REGISTRATION

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    # check to fix the retro-compatibility problem with the bug
    if isinstance(character.current_hit_points, str):
        character.current_hit_points = int(character.current_hit_points)
    character.current_hit_points -= int(damage)

    await update.effective_message.reply_text(f"{damage} danni subiti!")

    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_healing_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await update.effective_message.reply_text("Di quanto ti vuoi curare?")

    return HEALING_REGISTRATION


async def character_healing_registration_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    healing = update.effective_message.text

    if not healing or healing.isalpha():
        await update.effective_message.reply_text("🔴 Inserisci un numero non una parola!")
        return HEALING_REGISTRATION

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    # check to fix the retro-compatibility problem with the bug
    if isinstance(character.current_hit_points, str):
        character.current_hit_points = int(character.current_hit_points)
    character.current_hit_points += int(healing)

    await update.effective_message.reply_text(f"Sei stato curato di {healing} PF!")

    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_hit_points_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    await update.effective_message.reply_text(f"Quanti sono ora i punti ferita di {character.name}?\n\n"
                                              f"N.B. I punti ferita attuali saranno ripristinati al massimo!")

    return HIT_POINTS_REGISTRATION


async def character_hit_points_registration_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    hit_points = update.effective_message.text

    if not hit_points or hit_points.isalpha():
        await update.effective_message.reply_text("🔴 Inserisci un numero non una parola!")
        return HIT_POINTS_REGISTRATION

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    # check to fix the retro-compatibility problem with the bug
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

    message_str = (f"<b>Stai per effettuare un riposo lungo!</b>\n\n"
                   f"Questo comporta:\n"
                   f"- Ripristino dei punti ferita\n"
                   f"- Ripristino slot incantesimo\n\n"
                   f"Vuoi procedere? Usa /stop per annullare")
    keyboard = [[InlineKeyboardButton("Riposa", callback_data=LONG_REST_CALLBACK_DATA)]]

    await update.effective_message.reply_text(message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                                  parse_mode=ParseMode.HTML)

    return LONG_REST


async def character_long_rest_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.long_rest()

    await query.answer("Riposo lungo effettuato!", show_alert=True)

    msg, reply_markup = create_main_menu_message(character)
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_short_rest_warning_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = (f"<b>Stai per effettuare un riposo breve!</b>\n\n"
                   f"Questo comporta il ripristino di quelle abilità che lo prevedono in caso di riposo breve.\n"
                   f"Per ora non ricarica gli slot incantesimo che prevedono di ricaricarsi con il riposo breve come quelli del Warlock.\n\n"
                   f"Vuoi procedere? Usa /stop per annullare")
    keyboard = [[InlineKeyboardButton("Riposa", callback_data=SHORT_REST_CALLBACK_DATA)]]

    await update.effective_message.reply_text(message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                                  parse_mode=ParseMode.HTML)

    return SHORT_REST


async def character_short_rest_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.short_rest()

    await query.answer("Riposo breve effettuato!", show_alert=True)

    msg, reply_markup = create_main_menu_message(character)
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


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


async def send_dice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_edit: bool = True):
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    roll_history = character.get_rolls_history()
    message_str = (f"<b>Gestione tiri di dado</b>\n\n"
                   f"<code>{roll_history if roll_history != '' else 'Cronologia lanci vuota!\n\n'}</code>"
                   "Seleziona quanti dadi vuoi tirare:\n\n")

    if is_edit:
        starting_dice = context.user_data[CHARACTERS_CREATOR_KEY][DICE]
        reply_markup = create_dice_keyboard(starting_dice)
    else:
        starting_dice = STARTING_DICE.copy()
        reply_markup = create_dice_keyboard(starting_dice)
        context.user_data[CHARACTERS_CREATOR_KEY][DICE] = starting_dice

    if is_edit:
        message = await update.effective_message.edit_text(message_str, reply_markup=reply_markup,
                                                           parse_mode=ParseMode.HTML)
    else:
        message = await update.effective_message.reply_text(message_str, reply_markup=reply_markup,
                                                            parse_mode=ParseMode.HTML)

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
