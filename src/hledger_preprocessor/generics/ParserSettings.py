from typing import List, Protocol


class ParserSettings(Protocol):
    def get_field_names(self) -> List[str]: ...

    def uses_header(self) -> bool: ...
