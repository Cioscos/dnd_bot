from typing import List, Optional

from src.model.APIResource import APIResource


class AbilityScore(APIResource):
    full_name: str
    desc: List[str]
    skills: Optional[List[APIResource]]
    url: str

    def __repr__(self):
        self.__str__()

    def __str__(self):
        return (f"<br>Nome</br>: {self.full_name}\n"
                f"<br>Descrizione</br>: {" ".join(self.desc)}\n"
                f"<br>Skills</br>: {', '.join([skill.name for skill in self.skills])}")
