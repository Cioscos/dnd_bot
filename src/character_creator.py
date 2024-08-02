import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

logger = logging.getLogger(__name__)

# bot data keys
BOT_DATA_CHAT_IDS = 'bot_data_chat_ids'

# chat data keys
WIKI = 'wiki'
CHARACTERS_CREATOR = 'characters_creator'

# State definitions for top-level conv handler
START_MENU, WIKI_MENU, CHARACTERS_CREATOR_MENU, ITEM_DETAILS_MENU = map(chr, range(4))

# State definitions for class sub conversation
CLASS_SUBMENU, CLASS_SPELLS_SUBMENU, CLASS_RESOURCES_SUBMENU, CLASS_MANUAL_SPELLS_SEARCHING, CLASS_READING_SPELLS_SEARCHING, CLASS_SPELL_VISUALIZATION = map(
    chr, range(4, 10))

# state definitions for equipment-categories conversation
EQUIPMENT_CATEGORIES_SUBMENU, EQUIPMENT_VISUALIZATION = map(chr, range(10, 12))

# state definitions for features conversation
FEATURES_SUBMENU, FEATURE_VISUALIZATION = map(chr, range(12, 14))


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

    await update.effective_message.reply_text("<b>Questa sezione è ancora in sviluppo!</b>\n"
                                              "Visita la <a href=\"https://github.com/Cioscos/dnd_bot\">pagina Github"
                                              "</a> del progetto per saperne di più.", parse_mode=ParseMode.HTML)

    return ConversationHandler.END
