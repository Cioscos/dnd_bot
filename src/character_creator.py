import logging
from typing import List, Tuple, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes, ConversationHandler

from src.model.character_creator.Ability import Ability
from src.model.character_creator.Character import Character
from src.model.character_creator.Item import Item
from src.model.character_creator.MultiClass import MultiClass
from src.model.character_creator.Spell import Spell, SpellLevel
from src.util import chunk_list, generate_abilities_list_keyboard, generate_spells_list_keyboard

logger = logging.getLogger(__name__)

CHARACTER_CREATOR_VERSION = "0.0.1"

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
 MULTICLASSING_ACTIONS) = map(int, range(14, 36))

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
CURRENT_SPELL_KEY = 'current_spell'
# Keys to store the data allowing a rollback in the case user use /stop command before ending the multiclass deleting
PENDING_REASSIGNMENT = 'pending_reassignment'
REMOVED_CLASS_LEVEL = 'removed_class_level'
REMAINING_CLASSES = 'remaining_classes'

# Main menu callback keys
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
ABILITY_BACK_MENU_CALLBACK_DATA = "ability_back_menu"
SPELL_LEARN_CALLBACK_DATA = "spells_learn"
SPELL_EDIT_CALLBACK_DATA = "spell_edit"
SPELL_DELETE_CALLBACK_DATA = "spell_delete"
SPELL_BACK_MENU_CALLBACK_DATA = "spell_back_menu"
LEVEL_UP_CALLBACK_DATA = "level_up"
LEVEL_DOWN_CALLBACK_DATA = "level_down"
MULTICLASSING_ADD_CALLBACK_DATA = "add_multiclass"
MULTICLASSING_REMOVE_CALLBACK_DATA = "remove_multiclass"


def create_main_menu_message(character: Character) -> Tuple[str, InlineKeyboardMarkup]:
    message_str = (f"Benvenuto nella gestione personaggio! v.{CHARACTER_CREATOR_VERSION}\n"
                   f"<b>Nome personaggio:</b> {character.name} L. {character.total_levels()}\n"
                   f"<b>Razza:</b> {character.race}\n"
                   f"<b>Genere:</b> {character.gender}\n"
                   f"<b>Classe:</b> {', '.join(f"{class_name} (Level {level})" for class_name, level in character.multi_class.classes.items())}\n\n"
                   f"<b>Punti ferita:</b> {character.hit_points} PF\n"
                   f"<b>Slot incantesimo</b>\n{"\n".join([f"{slot.slots_remaining()} di livello {level}" for level, slot in character.spell_slots.items()]) if character.spell_slots else "Non hai registrato ancora nessuno Slot incantesimo\n"}")

    message_str += (f"<b>Punti caratteristica</b>\n{str(character.feature_points)}\n\n"
                    f"<b>Peso trasportato:</b> {character.encumbrance} Lb")

    keyboard = [
        [
            InlineKeyboardButton('Level down', callback_data=LEVEL_DOWN_CALLBACK_DATA),
            InlineKeyboardButton('Level up', callback_data=LEVEL_UP_CALLBACK_DATA),
        ],
        [
            InlineKeyboardButton('Borsa', callback_data=BAG_CALLBACK_DATA),
            InlineKeyboardButton('Abilità', callback_data=ABILITIES_CALLBACK_DATA),
            InlineKeyboardButton('Spell', callback_data=SPELLS_CALLBACK_DATA)
        ],
        [InlineKeyboardButton('Gestisci slot incantesimo', callback_data=SPELLS_SLOT_CALLBACK_DATA)],
        [InlineKeyboardButton('Punti caratteristica', callback_data=FEATURE_POINTS_CALLBACK_DATA)],
        [InlineKeyboardButton('Gestisci multiclasse', callback_data=MULTICLASSING_CALLBACK_DATA)],
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

    character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    msg, reply_markup = create_main_menu_message(character)

    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    context.user_data[CHARACTERS_CREATOR_KEY].pop(TEMP_CHARACTER_KEY, None)
    context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_ITEM_KEY, None)

    return FUNCTION_SELECTION


async def character_creator_stop_nested(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text("Ok! Usa i comandi:\n"
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

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][TEMP_CHARACTER_KEY]
    character.multi_class.add_class(class_)

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
    return BAG_ITEM_EDIT


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

    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_spells_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

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


async def character_spells_menu_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        spell: Spell = next((spell for spell in character.spells if spell.name == data), None)
        message_str = (f"<b>Incantesimo:</b> {spell.name} Livello {spell.level.value}\n\n"
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

    spell_name, spell_desc, spell_level = spell_info.split("#", 2)
    if spell_name.isdigit() or spell_desc.isdigit() or spell_level.isalpha():
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
    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_spell_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    spell_info = update.effective_message.text

    spell_name, spell_desc, spell_level = spell_info.split("#", 2)
    if spell_name.isdigit() or spell_desc.isdigit() or spell_level.isalpha():
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

    spells = character.spells
    message_str = f"<b>Gestione incantesimi</b>\n\n"
    message_str += ("Usa /stop per tornare al menu\n"
                    "Ecco la lista degli incantesimi")

    spells_pages = chunk_list(spells, 8)
    context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY] = spells_pages
    current_page = spells_pages[context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]]

    reply_markup = generate_spells_list_keyboard(current_page)

    await update.effective_message.reply_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return SPELLS_MENU


async def character_abilities_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

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

    spells = character.spells

    message_str = f"<b>Gestione incantesimi</b>\n\n"
    if not character.abilities:

        message_str += "Non conosci ancora alcun incantesimo 🤷‍♂️"
        keyboard = [
            [InlineKeyboardButton("Impara nuovo incantesimo", callback_data=SPELL_LEARN_CALLBACK_DATA)]
        ]
        await update.effective_message.reply_text(message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                                  parse_mode=ParseMode.HTML)

        return ABILITY_LEARN

    else:
        message_str += ("Usa /stop per tornare al menu\n"
                        "Ecco la lista degli incantesimi")

        spells_pages = chunk_list(spells, 8)
        context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY] = spells_pages
        current_page = spells_pages[context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]]

        reply_markup = generate_spells_list_keyboard(current_page)

        await update.effective_message.reply_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

        return ABILITIES_MENU


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
        message_str = (f"<b>Abilità</b> {ability.name}\n\n"
                       f"<b>Descrizione</b>\n{ability.description}")
        keyboard = [
            [
                InlineKeyboardButton("Modifica", callback_data=ABILITY_EDIT_CALLBACK_DATA),
                InlineKeyboardButton("Dimentica", callback_data=ABILITY_DELETE_CALLBACK_DATA)
            ],
            [InlineKeyboardButton("Indietro 🔙", callback_data=ABILITY_BACK_MENU_CALLBACK_DATA)]
        ]
        await query.edit_message_text(message_str, reply_markup=InlineKeyboardMarkup(keyboard),
                                      parse_mode=ParseMode.HTML)

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
    await query.answer()
    data = query.data

    if data == ABILITY_EDIT_CALLBACK_DATA:
        await query.edit_message_text("Inviami l'abilità inserendo il nome e la descrizione separate da un #\n\n"
                                      "<b>Esempio:</b> <code>nome#bella descrizione</code>\n\n",
                                      parse_mode=ParseMode.HTML)

    elif data == ABILITY_DELETE_CALLBACK_DATA:

        keyboard = [
            [
                InlineKeyboardButton("Si", callback_data='y'),
                InlineKeyboardButton("No", callback_data='n')
            ]
        ]
        await query.edit_message_text("Sicuro di voler cancellare l'abilità?",
                                      reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == ABILITY_BACK_MENU_CALLBACK_DATA:

        ability_page = context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY][
            context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]]

        message_str = ("Usa /stop per tornare al menu\n"
                       "Ecco la lista delle abilità")
        reply_markup = generate_abilities_list_keyboard(ability_page)
        await query.edit_message_text(message_str, reply_markup=reply_markup)

        return ABILITIES_MENU

    return ABILITY_ACTIONS


async def character_ability_new_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await update.effective_message.reply_text(
        "Inviami l'abilità inserendo il nome e la descrizione separate da un #\n\n"
        "<b>Esempio:</b> <code>nome#bella descrizione</code>\n\n",
        parse_mode=ParseMode.HTML
    )

    return ABILITY_LEARN


async def character_ability_learn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ability_info = update.effective_message.text

    ability_name, ability_desc = ability_info.split("#", 1)
    if ability_name.isdigit() or ability_desc.isdigit():
        await update.effective_message.reply_text("🔴 Inserisci solo lettere non numeri!\n\n"
                                                  "Invia di nuovo l'abilità o usa /stop per terminare")
        return ABILITY_ACTIONS

    ability = Ability(ability_name, ability_desc)
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    if any(ability_name == ability.name for ability in character.abilities):
        await update.effective_message.reply_text("🔴 Hai già appreso questa abilità!\n\n"
                                                  "Invia un'altra abilità o usa /stop per terminare")
        return ABILITY_ACTIONS

    character.learn_ability(ability)
    await update.effective_message.reply_text("Abilità appresa con successo! ✅")
    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION


async def character_ability_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ability_info = update.effective_message.text

    ability_name, ability_desc = ability_info.split("#", 1)
    if ability_name.isdigit() or ability_desc.isdigit():
        await update.effective_message.reply_text("🔴 Inserisci solo lettere non numeri!\n\n"
                                                  "Invia di nuovo l'abilità o usa /stop per terminare")
        return ABILITY_ACTIONS

    old_ability: Ability = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_ABILITY_KEY]
    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]

    for ability in character.abilities:
        if ability.name == old_ability.name:
            ability.name = ability_name
            ability.description = ability_desc
            break

    await update.effective_message.reply_text("Abilità modificata con successo!")

    abilities = character.abilities
    message_str = f"<b>Gestione abilità</b>\n\n"
    message_str += ("Usa /stop per tornare al menu\n"
                    "Ecco la lista delle abilità")

    abilities_pages = chunk_list(abilities, 8)
    context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY] = abilities_pages
    current_page = abilities_pages[context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]]

    reply_markup = generate_abilities_list_keyboard(current_page)

    await update.effective_message.reply_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return ABILITIES_MENU


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

    abilities = character.abilities

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

        abilities_pages = chunk_list(abilities, 8)
        context.user_data[CHARACTERS_CREATOR_KEY][INLINE_PAGES_KEY] = abilities_pages
        current_page = abilities_pages[context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_INLINE_PAGE_INDEX_KEY]]

        reply_markup = generate_abilities_list_keyboard(current_page)

        await update.effective_message.reply_text(message_str, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

        return ABILITIES_MENU


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
        await query.edit_message_text("Scegli quale classe livellare in positivo o negativo:", reply_markup=keyboard)
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
    class_name, class_level = multi_class_info.split("#", maxsplit=1)

    if not class_name or class_name.isdigit() or not class_level or class_level.isalpha():
        await update.effective_message.reply_text("🔴 Hai inviato il messaggio in un formato sbagliato!\n\n"
                                                  "Invialo come classe#livello")

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

    await update.effective_message.reply_text("Sei sicuro di voler chancellare il personaggio?\n\n"
                                              f"{character.name} - classe {', '.join(f"{class_name} (Level {level})" for class_name, level in character.multi_class.classes.items())} di L. {character.total_levels()}",
                                              reply_markup=InlineKeyboardMarkup(keyboard))

    return CHARACTER_DELETION


async def character_deleting_answer_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == AFFERMATIVE_CHARACTER_DELETION_CALLBACK_DATA:

        # Deleting current character selection
        current_character: Character = context.user_data[CHARACTERS_CREATOR_KEY].pop(CURRENT_CHARACTER_KEY, None)

        characters: List[Character] = context.user_data[CHARACTERS_CREATOR_KEY][CHARACTERS_KEY]

        for character in characters:
            if character.name == current_character.name:
                characters.remove(character)

        await update.effective_message.reply_text("Personaggio eliminato con successo ✅")

    elif data == NEGATIVE_CHARACTER_DELETION_CALLBACK_DATA:

        await update.effective_message.reply_text("Eliminazione personaggio annullata")

    return await character_creator_stop(update, context)


async def character_spells_slots_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await update.effective_message.reply_text("Funzione ancora non implementata")

    character: Character = context.user_data[CHARACTERS_CREATOR_KEY][CURRENT_CHARACTER_KEY]
    msg, reply_markup = create_main_menu_message(character)
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return FUNCTION_SELECTION
