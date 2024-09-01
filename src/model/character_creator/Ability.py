from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RestorationType(Enum):
    SHORT_REST = "short"
    LONG_REST = "long"


@dataclass
class Ability:
    VERSION = 2
    name: Optional[str] = field(default=None)
    description: Optional[str] = field(default=None)
    is_passive: Optional[bool] = field(default=None)
    restoration_type: Optional[RestorationType] = field(default=None)

    _version: int = field(default_factory=int)

    def __post_init__(self):
        # If the object does not have the version, migration is necessary
        if not hasattr(self, '_version'):
            self._version = 1
        if self._version < Ability.VERSION:
            self.__migrate()

    def __migrate(self):
        """Migrates the data to the current version of the class."""
        if self._version < 2:
            # Migration for version 2
            self.is_passive = self.is_passive if hasattr(self, 'is_passive') else None
            self.restoration_type = self.restoration_type if hasattr(self, 'restoration_type') else None
            # Update version's object
            self._version = 2
        # FUTURE MIGRATIONS

    def __setstate__(self, state):
        """Method called during deserialisation"""
        # Updates the status of the object
        self.__dict__.update(state)

        # If the deserialised object does not have a version, we set the default version
        if not hasattr(self, '_version'):
            self._version = 1

        # Migrate if necessary
        if self._version < Ability.VERSION:
            self.__migrate()

    def __str__(self) -> str:
        return (f"Ability(name={self.name}, description={self.description}, "
                f"is_passive={self.is_passive}, restoration_type={self.restoration_type})")

    def __repr__(self) -> str:
        return (f"Ability(name={self.name!r}, description={self.description!r}, "
                f"is_passive={self.is_passive!r}, restoration_type={self.restoration_type!r})")
