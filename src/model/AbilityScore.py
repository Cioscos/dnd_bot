from typing import List

from src.model.APIResource import APIResource


class AbilityScore(APIResource):
    def __init__(self, index: str, name: str, url: str, full_name: str, desc: List[str], skills: List[APIResource]):
        super().__init__(index, name, url)
        self.full_name = full_name
        self.desc = desc
        self.skills = skills

    def __repr__(self):
        repr_string = (f"*{self.full_name} ({self.name})*:\n"
                       f"{" ".join(self.desc)}\n\n"
                       f"*Skill*:\n{', '.join([skill.name for skill in self.skills]) if self.skills else 'No skills for this ability'}")
        return repr_string
