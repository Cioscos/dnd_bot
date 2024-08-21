from dataclasses import field, dataclass
from typing import List, Optional, Dict

from src.model.character_creator.Ability import Ability
from src.model.character_creator.FeaturePoints import FeaturePoints
from src.model.character_creator.Item import Item
from src.model.character_creator.MultiClass import MultiClass
from src.model.character_creator.SpellSlot import SpellSlot
from src.model.models import Spell


@dataclass
class Character:
    name: Optional[str] = field(default=None)
    race: Optional[str] = field(default=None)
    gender: Optional[str] = field(default=None)
    class_: Optional[str] = field(default=None)
    subClass: Optional[str] = field(default=None)
    multi_class: MultiClass = field(default_factory=MultiClass)
    level: int = 1
    feature_points: FeaturePoints = field(default_factory=FeaturePoints)
    spell_slots: Dict[int, SpellSlot] = field(default_factory=dict)
    bag: List[Item] = field(default_factory=list)
    spells: List[Spell] = field(default_factory=list)
    abilities: List[Ability] = field(default_factory=list)

    def level_up(self):
        """Increase character's level by 1."""
        self.level += 1

    def add_item(self, item: Item):
        """Add an item to the character's bag."""
        self.bag.append(item)

    def remove_item(self, item_name: str):
        """Remove an item from the character's bag by name."""
        self.bag = [item for item in self.bag if item.name != item_name]

    def list_items(self):
        """List all items in the character's bag."""
        return [str(item) for item in self.bag]

    def learn_spell(self, spell: Spell):
        """Adds a spell to the character's spellbook."""
        self.spells.append(spell)

    def forget_spell(self, spell_name: str):
        """Removes a spell from the character's spellbook by name."""
        self.spells = [spell for spell in self.spells if spell.name != spell_name]

    def list_spells(self):
        """Lists all spells the character has learned."""
        return [str(spell) for spell in self.spells]

    def learn_ability(self, ability: Ability):
        """Adds an ability to the character's abilities list."""
        self.abilities.append(ability)

    def forget_ability(self, ability_name: str):
        """Removes an ability from the character's abilities list by name."""
        self.abilities = [ability for ability in self.abilities if ability.name != ability_name]

    def list_abilities(self):
        """Lists all abilities the character has learned."""
        return [str(ability) for ability in self.abilities]

    def add_spell_slot(self, spell_slot: SpellSlot):
        """Adds or updates a spell slot at a given level."""
        self.spell_slots[spell_slot.level] = spell_slot

    def use_spell_slot(self, level: int):
        """Uses a spell slot at the specified level."""
        if level not in self.spell_slots:
            raise ValueError(f"No spell slots available at level {level}.")
        self.spell_slots[level].use_slot()

    def restore_spell_slot(self, level: int):
        """Restores a used spell slot at the specified level."""
        if level not in self.spell_slots:
            raise ValueError(f"No spell slots available at level {level}.")
        self.spell_slots[level].restore_slot()

    def restore_all_spell_slots(self):
        """Restores all used spell slots."""
        for slot in self.spell_slots.values():
            slot.restore_all_slots()

    def add_class(self, class_name: str, levels: int = 1):
        """Adds levels to a specified class using multiclassing."""
        self.multi_class.add_class(class_name, levels)

    def remove_class(self, class_name: str):
        """Removes a class from the character's multiclass."""
        self.multi_class.remove_class(class_name)

    def get_class_level(self, class_name: str) -> Optional[int]:
        """Gets the level of a specified class."""
        return self.multi_class.get_class_level(class_name)

    def list_classes(self) -> str:
        """Lists all classes and their levels for the character."""
        return self.multi_class.list_classes()

    def total_levels(self) -> int:
        """Returns the total number of levels across all classes."""
        return self.multi_class.total_levels()

    def list_spell_slots(self):
        """Lists all spell slots and their statuses."""
        return [str(slot) for slot in self.spell_slots.values()]

    def __str__(self):
        return (f"Character(name={self.name}, race={self.race}, gender={self.gender}, "
                f"class_={self.class_}, level={self.level}, multi_class={self.multi_class}, "
                f"feature_points={self.feature_points}, items={len(self.bag)}, "
                f"spells={len(self.spells)}, abilities={len(self.abilities)}, "
                f"spell_slots={len(self.spell_slots)})")

    def __repr__(self):
        return (f"Character(name={self.name!r}, race={self.race!r}, gender={self.gender!r}, "
                f"class_={self.class_!r}, level={self.level!r}, multi_class={self.multi_class!r}, "
                f"feature_points={self.feature_points!r}, items={self.bag!r}, "
                f"spells={self.spells!r}, abilities={self.abilities!r}, "
                f"spell_slots={self.spell_slots!r})")
