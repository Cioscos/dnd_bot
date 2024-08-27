from dataclasses import field, dataclass
from enum import Enum
from typing import List, Optional, Dict

from src.model.character_creator.Ability import Ability
from src.model.character_creator.FeaturePoints import FeaturePoints
from src.model.character_creator.Item import Item
from src.model.character_creator.MultiClass import MultiClass
from src.model.character_creator.Spell import Spell
from src.model.character_creator.SpellSlot import SpellSlot


class SpellsSlotMode(Enum):
    AUTOMATIC = 'automatic'
    MANUAL = 'manual'


@dataclass
class Character:
    name: Optional[str] = field(default=None)
    race: Optional[str] = field(default=None)
    gender: Optional[str] = field(default=None)
    multi_class: MultiClass = field(default_factory=MultiClass)
    hit_points: int = field(default_factory=int)
    current_hit_points: int = field(default_factory=int)
    feature_points: FeaturePoints = field(default_factory=FeaturePoints)
    spell_slots_mode: SpellsSlotMode = field(default=None)
    spell_slots: Dict[int, SpellSlot] = field(default_factory=dict)
    MAX_SPELL_SLOT_LEVEL = 9
    bag: List[Item] = field(default_factory=list)
    spells: List[Spell] = field(default_factory=list)
    abilities: List[Ability] = field(default_factory=list)
    carry_capacity: int = field(default_factory=int)
    encumbrance: int = field(default_factory=int)

    def __post_init__(self):
        self.carry_capacity = self.feature_points.strength * 15
        self.encumbrance = sum([item.weight for item in self.bag])

    def __reload_stats(self):
        self.carry_capacity = self.feature_points.strength * 15
        self.encumbrance = sum([item.weight for item in self.bag])

    def add_item(self, item: Item):
        """Add an item to the character's bag and update the encumbrance."""
        # Check if the item already exists in the bag
        for existing_item in self.bag:
            if existing_item == item:
                # Item exists, update the quantity and encumbrance
                existing_item.quantity += item.quantity
                self.encumbrance += item.weight * item.quantity
                return

        # If the item doesn't exist, add it to the bag
        self.bag.append(item)
        self.encumbrance += item.weight * item.quantity

    def increment_item_quantity(self, item_name: str, quantity: int = 1):
        """Increment the quantity of an existing item in the character's bag by a certain amount."""
        for item in self.bag:
            if item.name == item_name:
                item.quantity += quantity
                self.encumbrance += item.weight * quantity
                return

    def decrement_item_quantity(self, item: str, quantity: int = 1):
        """Remove a specific quantity of an item from the character's bag by name."""
        for existing_item in self.bag:
            if existing_item.name == item:
                if existing_item.quantity > quantity:
                    # Reduce the quantity and update encumbrance
                    existing_item.quantity -= quantity
                    self.encumbrance -= existing_item.weight * quantity
                else:
                    # Remove the item completely and update encumbrance
                    self.bag.remove(existing_item)
                    self.encumbrance -= existing_item.weight * existing_item.quantity
                break

    def remove_item(self, item: Item):
        """Remove a specific item from the character's bag."""
        for existing_item in self.bag:
            if existing_item == item:
                # Update encumbrance based on the item's total weight and remove it from the bag
                self.encumbrance -= existing_item.weight * existing_item.quantity
                self.bag.remove(existing_item)
                break

    def list_items(self):
        """List all items in the character's bag."""
        return [str(item) for item in self.bag]

    def available_space(self):
        """Return how much weight is still supportable from the character"""
        return self.carry_capacity - self.encumbrance

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

    def total_classes(self) -> int:
        """Returns the total number of classes across all classes."""
        return len(self.multi_class.classes)

    def list_spell_slots(self):
        """Lists all spell slots and their statuses."""
        return [str(slot) for slot in self.spell_slots.values()]

    def change_feature_points(self, feature_points: Dict[str, int]):
        self.feature_points.points = feature_points
        self.__reload_stats()

    def __str__(self):
        return (f"Character(name={self.name}, race={self.race}, gender={self.gender}, "
                f"multi_class={self.multi_class}, "
                f"feature_points={self.feature_points}, items={len(self.bag)}, "
                f"spells={len(self.spells)}, abilities={len(self.abilities)}, "
                f"spell_slots={len(self.spell_slots)}), spell_slots_mode={self.spell_slots_mode}")

    def __repr__(self):
        return (f"Character(name={self.name!r}, race={self.race!r}, gender={self.gender!r}, "
                f"multi_class={self.multi_class!r}, "
                f"feature_points={self.feature_points!r}, items={self.bag!r}, "
                f"spells={self.spells!r}, abilities={self.abilities!r}, "
                f"spell_slots={self.spell_slots!r})")
