import math
from dataclasses import dataclass
from typing import Dict


@dataclass
class FeaturePoints:
    strength: int = 0
    dexterity: int = 0
    constitution: int = 0
    intelligence: int = 0
    wisdom: int = 0
    charisma: int = 0

    def _calculate_modifier(self, value: int) -> int:
        return math.floor((value - 10) / 2)

    @property
    def strength_modifier(self) -> int:
        return self._calculate_modifier(self.strength)

    @property
    def dexterity_modifier(self) -> int:
        return self._calculate_modifier(self.dexterity)

    @property
    def constitution_modifier(self) -> int:
        return self._calculate_modifier(self.constitution)

    @property
    def intelligence_modifier(self) -> int:
        return self._calculate_modifier(self.intelligence)

    @property
    def wisdom_modifier(self) -> int:
        return self._calculate_modifier(self.wisdom)

    @property
    def charisma_modifier(self) -> int:
        return self._calculate_modifier(self.charisma)

    @property
    def modifiers(self) -> Dict[str, int]:
        return {
            'strength': self.strength_modifier,
            'dexterity': self.dexterity_modifier,
            'constitution': self.constitution_modifier,
            'intelligence': self.intelligence_modifier,
            'wisdom': self.wisdom_modifier,
            'charisma': self.charisma_modifier
        }

    @property
    def points(self) -> Dict[str, int]:
        return {
            'strength': self.strength,
            'dexterity': self.dexterity,
            'constitution': self.constitution,
            'intelligence': self.intelligence,
            'wisdom': self.wisdom,
            'charisma': self.charisma
        }

    def __str__(self) -> str:
        return (f"Forza {self.strength} ({self.strength_modifier})\n"
                f"Destrezza {self.dexterity} ({self.dexterity_modifier})\n"
                f"Costituzione {self.constitution} ({self.constitution_modifier})\n"
                f"Intelligenza {self.intelligence} ({self.intelligence_modifier})\n"
                f"Saggezza {self.wisdom} ({self.wisdom_modifier})\n"
                f"Carisma {self.charisma} ({self.charisma_modifier})")

    def __eq__(self, other) -> bool:
        if not isinstance(other, FeaturePoints):
            return NotImplemented
        return (self.strength == other.strength and
                self.dexterity == other.dexterity and
                self.constitution == other.constitution and
                self.intelligence == other.intelligence and
                self.wisdom == other.wisdom and
                self.charisma == other.charisma)
