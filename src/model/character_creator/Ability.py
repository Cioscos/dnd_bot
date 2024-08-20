from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Ability:
    name: Optional[str] = field(default=None)
    description: Optional[str] = field(default=None)

    def __str__(self) -> str:
        return f"Ability(name={self.name}, description={self.description})"

    def __repr__(self) -> str:
        return f"Ability(name={self.name!r}, description={self.description!r})"
