from typing import List, Union

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

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


async def split_text_into_chunks(text: str, update: Update, max_length: int = 4096) -> None:
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
        await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
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
        await update.effective_message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


def generate_account_list_keyboard(entries: List[str],
                                   draw_navigation_buttons: bool = True) -> InlineKeyboardMarkup:
    """
    Generates an inline keyboard markup for the provided list of accounts.

    Args:
        accounts (List[Account]): List of Account objects.
        draw_navigation_buttons (bool): Choose to draw or not the navigation buttons

    Returns:
        InlineKeyboardMarkup: The generated inline keyboard markup.
    """
    keyboard = []

    row = []
    for entry in entries:
        button = InlineKeyboardButton(entry, callback_data=f"{ABILITY_SCORE_CALLBACK}:{account.id}")
        row.append(button)

        if len(row) == 2:
            keyboard.append(row)
            row = []

    # Append any remaining buttons if the total is an odd number
    if row:
        keyboard.append(row)

    if draw_navigation_buttons:
        # Add navigation buttons
        navigation_buttons = [InlineKeyboardButton("Previous", callback_data="prev_page"),
                              InlineKeyboardButton("Next", callback_data="next_page")]
        keyboard.append(navigation_buttons)

    return InlineKeyboardMarkup(keyboard)


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
