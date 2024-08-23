import logging
from typing import List, Tuple, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes, ConversationHandler

from src.model.character_creator.Character import Character
from src.model.character_creator.Item import Item

logger = logging.getLogger(__name__)

CHARACTER_CREATOR_VERSION = "0.0.1"

# states definition
(CHARACTER_CREATION, CHARACTER_SELECTION, NAME_SELECTION, RACE_SELECTION, GENDER_SELECTION,
 CLASS_SELECTION, HIT_POINTS_SELECTION, FUNCTION_SELECTION, BAG_MANAGEMENT, CHARACTER_DELETION, BAG_ITEM_INSERTION,
 BAG_ITEM_EDIT, FEATURE_POINTS_EDIT) = map(int, range(14, 27))

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
BAG_ITEM_INSERTION_CALLBACK_DATA = "bag_insert_item"
BAG_ITEM_EDIT_CALLBACK_DATA = "bag_edit_item"


def create_main_menu_message(character: Character) -> Tuple[str, InlineKeyboardMarkup]:
    message_str = (f"Benvenuto nella gestione personaggio! v.{CHARACTER_CREATOR_VERSION}\n"
                   f"<b>Nome personaggio:</b> {character.name} L. {character.level}\n"
                   f"<b>Razza:</b> {character.race}\n"
                   f"<b>Genere:</b> {character.gender}\n"
                   f"<b>Classe:</b> {character.class_}\n\n"
                   f"<b>Punti ferita:</b> {character.hit_points} PF\n"
                   f"<b>Slot incantesimo</b>\n{"\n".join([f"{slot.slots_remaining()} di livello {level}" for level, slot in character.spell_slots.items()]) if character.spell_slots else "Non hai registrato ancora nessuno Slot incantesimo\n"}")

    message_str += (f"<b>Punti caratteristica</b>\n{str(character.feature_points)}\n\n"
                    f"<b>Peso trasportato:</b> {character.encumbrance} Lb")

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


async def character_creator_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    msg, reply_markup = create_main_menu_message(character)

    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_CHARACTER_KEY, None)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ITEM_KEY, None)

    return FUNCTION_SELECTION


async def character_creator_stop_nested(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Ok! Usa i comandi:\n"
                                    "/wiki per consultare la wiki\n"
                                    "/character per usare il gestore di personaggi")

    context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_CHARACTER_KEY, None)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_CHARACTER_KEY, None)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ITEM_KEY, None)

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

    await update.effective_message.reply_text(
        "Quanti punti vita ha il tuo personaggio?\nRispondi a questo messaggio o premi /stop per terminare")

    return HIT_POINTS_SELECTION


async def character_hit_points_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    hit_points = update.effective_message.text

    character = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY]
    character.hit_points = hit_points

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
    message_str = (f"<b>Oggetti nella borsa</b>\n\n"
                   f"{'\n'.join(f'<code>{item.name}</code> x{item.quantity}' for item in character.bag) if character.bag else 
                   "Lo zaino è ancora vuoto"}")

    keyboard = [[InlineKeyboardButton('Inserisci nuovo oggetto', callback_data=BAG_ITEM_INSERTION_CALLBACK_DATA)]]

    if character.bag:
        keyboard.append([InlineKeyboardButton('Modifica oggetto', callback_data=BAG_ITEM_EDIT)])

    await update.effective_message.reply_text(
        message_str,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

    return BAG_MANAGEMENT


async def character_bag_new_object_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_str = (f"Rispondi con il nome dell'oggetto e la quantità!\n"
                   f"Premi /stop per terminare\n\n"
                   f"<b>Esempio:</b> <code>Pozione di guarigione superiore#2#Mi cura 8d4 + 8 di vita#1</code>\n"
                   f"Il peso è opzionale!")

    await update.effective_message.reply_text(message_str, parse_mode=ParseMode.HTML)

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
        msg, reply_markup = create_main_menu_message(character)
        await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return FUNCTION_SELECTION

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

    # Update the main menu
    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


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

    message_str = (f"<b>Nome:</b> <code>{item.name}</code>\n"
                   f"<b>Descrizione:</b> <code>{item.description}</code>\n"
                   f"<b>Quantità:</b> <code>{item.quantity}</code>\n\n"
                   f"Premi /stop per terminare\n\n")

    context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ITEM_KEY] = item.name

    keyboard = [
        [
            InlineKeyboardButton("-", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|-"),
            InlineKeyboardButton("+", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|+")
        ],
        [InlineKeyboardButton("Rimuovi tutti", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|all")]
    ]

    await update.effective_message.reply_text(message_str, parse_mode=ParseMode.HTML,
                                              reply_markup=InlineKeyboardMarkup(keyboard))
    return BAG_ITEM_EDIT


async def character_bag_item_delete_one_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    item_name = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ITEM_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.decrement_item_quantity(item_name)
    item: Item = next((item for item in character.bag if item_name == item.name), None)

    message_str = (f"<b>Nome:</b> <code>{item.name}</code>\n"
                   f"<b>Descrizione:</b> <code>{item.description}</code>\n"
                   f"<b>Quantità:</b> <code>{item.quantity}</code>\n\n"
                   f"Premi /stop per terminare\n\n")
    keyboard = [
        [
            InlineKeyboardButton("-", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|-"),
            InlineKeyboardButton("+", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|+")
        ],
        [InlineKeyboardButton("Rimuovi tutti", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|all")]
    ]

    await query.edit_message_text(message_str, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))


async def character_bag_item_add_one_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    item_name = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ITEM_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    character.increment_item_quantity(item_name)
    item: Item = next((item for item in character.bag if item_name == item.name), None)

    message_str = (f"<b>Nome:</b> <code>{item.name}</code>\n"
                   f"<b>Descrizione:</b> <code>{item.description}</code>\n"
                   f"<b>Quantità:</b> <code>{item.quantity}</code>\n\n"
                   f"Premi /stop per terminare\n\n")
    keyboard = [
        [
            InlineKeyboardButton("-", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|-"),
            InlineKeyboardButton("+", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|+")
        ],
        [InlineKeyboardButton("Rimuovi tutti", callback_data=f"{BAG_ITEM_EDIT_CALLBACK_DATA}|all")]
    ]

    await query.edit_message_text(message_str, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))


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
        await query.answer("Non puoi andare sotto lo zero")
        return FEATURE_POINTS_EDIT

    character.change_feature_points(feature_points)

    # Update the message with the new feature points
    messagges: Dict[str, Tuple[str, InlineKeyboardMarkup]] = create_feature_points_messages(feature_points)

    text, keyboard = messagges[feature]
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await query.answer()

    return FEATURE_POINTS_EDIT


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
