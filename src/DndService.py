from typing import Dict
import aiohttp


class DndService:
    def __init__(self):
        """
        Initialize the DndService with the base API URL, payload, and headers.
        """
        self.__api = "https://www.dnd5eapi.co"
        self.__payload = {}
        self.__headers = {
            'Accept': 'application/json'
        }
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

    async def __do_get(self, url: str) -> Dict:
        """
        Fetch data from a specific API URL.

        Args:
            url (str): The API URL to fetch data from.

        Returns:
            dict: The JSON response from the API.
        """
        async with self.__session.get(url, headers=self.__headers) as response:
            response.raise_for_status()
            return await response.json()

    async def get_ability_score(self, ability: str) -> Dict:
        """
        Fetch data from a specific API ability score.

        Args:
            ability (str): Ability score to fetch. Possible values: [cha, con, dex, int, str, wis]

        Returns:
            dict: The JSON response from the API.

        Raises:
            ValueError: If the ability is not one of the allowed values.
        """
        if ability not in ["cha", "con", "dex", "int", "str", "wis"]:
            raise ValueError("Ability must be either cha, con, dex, int, str, wis")
        url = f"{self.__api}/api/ability-scores/{ability}"
        return await self.__do_get(url)

    async def get_ability_scores(self) -> Dict:
        """
        Fetch ability scores.
        """
        url = f"{self.__api}/api/ability-scores"
        return await self.__do_get(url)
