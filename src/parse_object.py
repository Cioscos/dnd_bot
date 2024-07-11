from typing import Any, Dict

from src.model.APIResource import APIResource
from src.model.AbilityScore import AbilityScore


def parse_ability_score(data: Dict[str, Any]) -> AbilityScore:
    skills = [APIResource(skill['index'], skill['name'], skill['url']) for skill in data.get('skills', [])]
    return AbilityScore(
        data['index'],
        data['name'],
        data['url'],
        data['full_name'],
        data['desc'],
        skills
    )
