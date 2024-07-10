import aiohttp
import asyncio
from typing import Dict


class TranslationService:
    def __init__(self):
        """
        Initialize the TranslationService with the base API URL.
        """
        self.__api_url = "https://655.mtis.workers.dev/translate"
        self.__session = None

    async def __aenter__(self):
        """
        Async context manager entry. Initialize the aiohttp session.
        """
        self.__session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """
        Async context manager exit. Close the aiohttp session.
        """
        await self.__session.close()

    async def translate(self, text: str, source_lang: str = "en", target_lang: str = "it") -> Dict:
        """
        Translate the given text using the specified API.

        Args:
            text (str): The text to translate.
            source_lang (str): The source language (default is "en").
            target_lang (str): The target language (default is "it").

        Returns:
            Dict: The JSON response from the API.
        """
        params = {
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang
        }

        async with self.__session.get(self.__api_url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            return data['response']['translated_text']
