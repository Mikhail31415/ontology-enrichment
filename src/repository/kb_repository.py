from typing_extensions import Protocol


class KBRepository(Protocol):
    def add_individuals(self, collection: dict) -> None:
        ...

