from typing import List, Union

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from src.model.APIResource import APIResource

ABILITY_SCORE_CALLBACK = 'ability_score'


def is_string_in_nested_lists(target: str, nested_lists: List[Union[str, List]]) -> bool:
    """
    Check if a string is present in a list of nested lists.

    Args:
        target (str): The string to search for.
        nested_lists (List[Union[str, List]]): The list of nested lists.

    Returns:
        bool: True if the string is found, False otherwise.
    """
    for item in nested_lists:
        if isinstance(item, list):
            if is_string_in_nested_lists(target, item):
                return True
        elif isinstance(item, str) and item == target:
            return True
    return False


async def split_text_into_chunks(text: str, update: Update, reply_markup: InlineKeyboardMarkup = None, max_length: int = 4096) -> None:
    """
    Split a given text into chunks that do not exceed the maximum Telegram message length.

    Args:
        text (str): The text to be split.
        update (Update): The bot update object.
        max_length (int): The maximum length of each chunk (default is 4096).

    Returns:
        List[str]: A list of text chunks.
    """
    if len(text) <= max_length:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return

    chunks = []
    while len(text) > max_length:
        # Find the last space within the allowed length to avoid breaking words
        split_point = text.rfind(' ', 0, max_length)
        if split_point == -1:
            split_point = max_length  # If no space is found, split at the max_length
        chunks.append(text[:split_point])
        text = text[split_point:].strip()
    chunks.append(text)  # Add the last remaining part

    for chunk in chunks:
        await update.effective_message.reply_text(chunk, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


def generate_resource_list_keyboard(resources: List[APIResource],
                                    draw_navigation_buttons: bool = True) -> InlineKeyboardMarkup:
    """
    Generates an inline keyboard markup for the provided list of accounts.

    Args:
        resources (List[Account]): List of Account objects.
        draw_navigation_buttons (bool): Choose to draw or not the navigation buttons

    Returns:
        InlineKeyboardMarkup: The generated inline keyboard markup.
    """
    keyboard = []
    row = []
    for resource in resources:
        button = InlineKeyboardButton(resource.name, callback_data=f"{resource.url}")
        row.append(button)

        if len(row) == 2:
            keyboard.append(row)
            row = []

    # Append any remaining buttons if the total is an odd number
    if row:
        keyboard.append(row)

    if draw_navigation_buttons:
        # Add navigation buttons
        navigation_buttons = [InlineKeyboardButton("⬅️ Precedente", callback_data="prev_page"),
                              InlineKeyboardButton("Successiva ➡️", callback_data="next_page")]
        keyboard.append(navigation_buttons)

    return InlineKeyboardMarkup(keyboard)


def chunk_list(input_list, chunk_size):
    """
    Divide una lista in sottoliste di dimensione massima `chunk_size`.

    Args:
        input_list (list): La lista da dividere.
        chunk_size (int): La dimensione massima di ogni sottolista.

    Returns:
        list of lists: Una lista contenente sottoliste di massimo `chunk_size` elementi.
    """
    # Utilizza una list comprehension per creare i chunk
    return [input_list[i:i + chunk_size] for i in range(0, len(input_list), chunk_size)]


def format_camel_case_to_title(input_string: str) -> str:
    """
    Converts a hyphen-separated string into a properly capitalized string with spaces.

    Args:
        input_string (str): The input string in hyphen-separated format.

    Returns:
        str: The formatted string with each word capitalized and separated by spaces.
    """
    words = input_string.split('-')
    formatted_string = ' '.join(word.capitalize() for word in words)
    return formatted_string
