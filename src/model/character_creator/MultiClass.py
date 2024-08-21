from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class MultiClass:
    classes: Dict[str, int] = field(default_factory=dict)

    def add_class(self, class_name: str, levels: int = 1):
        """Adds levels to a specified class. If the class does not exist, it is added."""
        if levels < 1:
            raise ValueError("Levels to add must be a positive integer.")
        if class_name in self.classes:
            self.classes[class_name] += levels
        else:
            self.classes[class_name] = levels

    def remove_class(self, class_name: str):
        """Removes a class entirely from the multiclass list."""
        if class_name in self.classes:
            del self.classes[class_name]
        else:
            raise ValueError(f"Class {class_name} does not exist in this multiclass.")

    def get_class_level(self, class_name: str) -> Optional[int]:
        """Returns the level of the specified class, or None if the class is not present."""
        return self.classes.get(class_name, None)

    def total_levels(self) -> int:
        """Returns the total number of levels across all classes."""
        return sum(self.classes.values())

    def list_classes(self) -> str:
        """Returns a string listing all classes and their levels."""
        return ', '.join(f"{class_name} (Level {level})" for class_name, level in self.classes.items())

    def __str__(self):
        return f"MultiClass(classes={self.classes})"

    def __repr__(self):
        return f"MultiClass(classes={self.classes!r})"
