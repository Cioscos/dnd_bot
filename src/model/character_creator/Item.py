from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Item:
    name: str
    description: Optional[str] = field(default=None)
    quantity: int = 0
    weight: int = 0

    def __post_init__(self):
        # Validation for name and description
        if not self.name:
            raise ValueError("Item name cannot be empty.")
        if self.description is None:
            self.description = ""  # Default to empty string if no description provided

        # Validation for quantity
        if not isinstance(self.quantity, int) or self.quantity < 0:
            raise ValueError("Quantity must be a non-negative integer.")

    def __str__(self):
        desc = self.description if self.description else "No description provided"
        return f"Item(name={self.name}, description={desc}, quantity={self.quantity})"

    def __repr__(self):
        return f"Item(name={self.name!r}, description={self.description!r}, quantity={self.quantity!r})"

    def __eq__(self, other):
        if not isinstance(other, Item):
            return NotImplemented
        return self.name == other.name

    def increase_quantity(self, amount: int):
        """Increase the quantity by the given amount."""
        if amount < 0:
            raise ValueError("Increase amount must be non-negative.")
        self.quantity += amount

    def decrease_quantity(self, amount: int):
        """Decrease the quantity by the given amount."""
        if amount < 0:
            raise ValueError("Decrease amount must be non-negative.")
        if amount > self.quantity:
            raise ValueError("Cannot decrease quantity below zero.")
        self.quantity -= amount
