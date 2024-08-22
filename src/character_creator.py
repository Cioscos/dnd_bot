import logging
from typing import List, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes, ConversationHandler

from src.model.character_creator.Character import Character

logger = logging.getLogger(__name__)

CHARACTER_CREATOR_VERSION = "0.0.1"

# states definition
(CHARACTER_CREATION, CHARACTER_SELECTION, NAME_SELECTION, RACE_SELECTION, GENDER_SELECTION,
 CLASS_SELECTION, FUNCTION_SELECTION, CHARACTER_DELETION) = map(int, range(14, 22))

STOPPING = 99

# bot data keys
BOT_DATA_CHAT_IDS = 'bot_data_chat_ids'

# user_data keys
# we use the user_data because this function is for private use only
CHARACTERS_CREATOR_KEY = 'characters_creator'
CHARACTERS_KEY = 'characters'
TEMP_CHARACTER_KEY = 'temp_character'
CURRENT_CHARACTER_KEY = 'current_character'

# Main menu callback keys
BAG_CALLBACK_DATA = 'bag'
SPELLS_CALLBACK_DATA = 'spells'
ABILITIES_CALLBACK_DATA = 'abilities'
FEATURE_POINTS_CALLBACK_DATA = 'feature_points'
SUBCLASS_CALLBACK_DATA = 'subclass'
MULTICLASSING_CALLBACK_DATA = 'multiclass'
DELETE_CHARACTER_CALLBACK_DATA = 'delete_character'
AFFERMATIVE_CHARACTER_DELETION_CALLBACK_DATA = 'yes_delete_character'
NEGATIVE_CHARACTER_DELETION_CALLBACK_DATA = 'no_delete_character'



def create_main_menu_message(character: Character) -> Tuple[str, InlineKeyboardMarkup]:
    message_str = (f"Benvenuto nella gestione personaggio! v.{CHARACTER_CREATOR_VERSION}\n"
                   f"<b>Nome personaggio:</b> {character.name} L. {character.level}\n"
                   f"<b>Razza:</b> {character.race}\n"
                   f"<b>Genere:</b> {character.gender}\n"
                   f"<b>Classe:</b> {character.class_}\n\n"
                   f"<b>Slot incantesimo</b>\n{"\n".join([f"{slot.slots_remaining()} di livello {level}" for level, slot in character.spell_slots.items()]) if character.spell_slots else "Non hai registrato ancora nessuno Slot incantesimo\n"}")

    message_str += f"<b>Punti caratteristica</b>\n{str(character.feature_points)}"

    keyboard = [
        [
            InlineKeyboardButton('Borsa', callback_data=BAG_CALLBACK_DATA),
            InlineKeyboardButton('Spell', callback_data=SPELLS_CALLBACK_DATA)
        ],
        [InlineKeyboardButton('Abilità', callback_data=ABILITIES_CALLBACK_DATA)],
        [InlineKeyboardButton('Punti caratteristica', callback_data=FEATURE_POINTS_CALLBACK_DATA)],
        [InlineKeyboardButton('Aggiungi sotto-classe', callback_data=SUBCLASS_CALLBACK_DATA)],
        [InlineKeyboardButton('Aggiungi multiclasse', callback_data=MULTICLASSING_CALLBACK_DATA)],
        [InlineKeyboardButton('Elimina personaggio', callback_data=DELETE_CHARACTER_CALLBACK_DATA)]
    ]

    return message_str, InlineKeyboardMarkup(keyboard)


async def character_creator_stop_nested(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text("Ok! Usa i comandi:\n"
                                    "/wiki per consultare la wiki\n"
                                    "/character per usare il gestore di personaggi")

    context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_CHARACTER_KEY, None)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_CHARACTER_KEY, None)

    return STOPPING

async def character_creator_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        query = update.callback_query
        await query.answer()

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
        "Qual'è il genere del personaggio?\nRispondi a questo messaggio o premi /stop per terminare")

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

    character = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY]
    character.class_ = class_

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

    await update.effective_message.reply_text("Funzione non ancora implementata")

    character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    msg, reply_markup = create_main_menu_message(character)

    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_spells_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await update.effective_message.reply_text("Funzione non ancora implementata")

    character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    msg, reply_markup = create_main_menu_message(character)

    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_abilities_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await update.effective_message.reply_text("Funzione non ancora implementata")

    character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    msg, reply_markup = create_main_menu_message(character)

    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_feature_point_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await update.effective_message.reply_text("Funzione non ancora implementata")

    character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    msg, reply_markup = create_main_menu_message(character)

    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_subclass_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await update.effective_message.reply_text("Funzione non ancora implementata")

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    msg, reply_markup = create_main_menu_message(character)

    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_multiclassing_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await update.effective_message.reply_text("Funzione non ancora implementata")

    character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
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

    await update.effective_message.reply_text("Sei sicuro di voler chancellare il personaggio?\n\n"
                                              f"{character.name} - classe {character.class_} di L. {character.level}",
                                              reply_markup=InlineKeyboardMarkup(keyboard))

    return CHARACTER_DELETION


async def character_deleting_answer_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # Deleting current character selection
    current_character: Character = context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_CHARACTER_KEY, None)

    characters: List[Character] = context.user_data[CHARACTERS_CREATOR_KEY][CHARACTERS_KEY]

    for character in characters:
        if character.name == current_character.name:
            characters.remove(character)

    await update.effective_message.reply_text("Personaggio eliminato con successo")

    return await character_creator_stop_nested(update, context)
