# Type alias for clarity
from dataclasses import dataclass
from typing import List, Tuple

from typeguard import typechecked

# Type alias for clarity: (Python field name, hledger field name)
# ColumnNames = List[Tuple[str, str]]
ColumnNames = Tuple[Tuple[str, str], ...]


@dataclass(frozen=True, unsafe_hash=True)
class CsvColumnMapping:
    """Stores the implicit order of CSV columns. with the transaction object attribute values left and the hledger field name right."""

    # Example: [['the_date', "date"], ['None', ''], ['tendered_amount_out', 'amount'], ...]
    csv_column_mapping: ColumnNames

    @typechecked
    def get_hledger_csv_column_names(self) -> List[str]:
        hledger_column_names: List[str] = []
        for pair in self.csv_column_mapping:
            tnx_attribute_name, hledger_column_name = pair
            hledger_column_names.append(hledger_column_name)
        return hledger_column_names
