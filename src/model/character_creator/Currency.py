from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class Currency:
    gold: int = 0
    silver: int = 0
    bronze: int = 0
    electrum: int = 0
    platinum: int = 0

    @property
    def currencies(self) -> Dict[str, Tuple[str, int]]:
        return {
            'gold': ('Oro', self.gold),
            'silver': ('Argento', self.silver),
            'bronze': ('Bronzo', self.bronze),
            'electrum': ('Electrum', self.electrum),
            'platinum': ('Platino', self.platinum)
        }