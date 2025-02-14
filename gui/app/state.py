from abc import ABC
from typing import Any, Dict, List
from pprint import pprint
import uuid

class StateContainer(ABC):
    pass

class TableStateContainer(StateContainer):
    def __init__(self):
        # Although we keep self.rows, our main data storage is in self.data_mapping.
        self.rows: List[List[Any]] = []
        self.columns: List[Dict[str, Any]] = []  # Each column is a dict with keys: "id", "default", and "raw"
        self.data_mapping: List[List[Any]] = []

    def __repr__(self) -> str:
        return f"Table with {len(self.columns)} cols and {len(self.rows)} rows"
    
    def get_columns(self) -> List[Dict[str, Any]]:
        """Return the list of columns (as dictionaries)."""
        return self.columns

    # --- Column CRUD operations ---

    def add_column(self, id: str, default: Any = None, raw: bool = False) -> None:
        """Create a new column with an optional default value and raw flag for existing rows."""
        if any(col["id"] == id for col in self.columns):
            raise ValueError(f"Column '{id}' already exists.")
        # Add the column with an extra 'raw' flag.
        self.columns.append({"id": id, "default": default, "raw": raw})
        # For each existing row, add the default value at the new column position.
        for row in self.data_mapping:
            row.append(default)

    def add_columns(self, column_names: List[Dict[str, Any]]) -> None:
        for col in column_names:
            # Expecting each dict may contain a "raw" key.
            self.add_column(col["id"], default=col.get("default", None), raw=col.get("raw", False))

    def get_column(self, column_name: str) -> List[Any]:
        """Return a list of values for the specified column."""
        for idx, col in enumerate(self.columns):
            if col["id"] == column_name:
                return [row[idx] for row in self.data_mapping]
        raise ValueError(f"Column '{column_name}' does not exist.")

    def update_column(self, old_name: str, new_name: str) -> None:
        """Update a column's name."""
        for col in self.columns:
            if col["id"] == old_name:
                if any(c["id"] == new_name for c in self.columns):
                    raise ValueError(f"Column '{new_name}' already exists.")
                col["id"] = new_name
                return
        raise ValueError(f"Column '{old_name}' does not exist.")

    def delete_column(self, column_name: str) -> None:
        """Delete a column from the table and remove its corresponding cell in each row."""
        index = None
        for i, col in enumerate(self.columns):
            if col["id"] == column_name:
                index = i
                break
        if index is None:
            raise ValueError(f"Column '{column_name}' does not exist.")
        self.columns.pop(index)
        for row in self.data_mapping:
            row.pop(index)

    # --- Row CRUD operations ---

    def add_row(self, row_data: Dict[str, Any]) -> None:
        """
        Insert a new row into the table.

        - If no columns have been defined yet, the keys of row_data are used to create the columns.
        - If columns exist, new keys in row_data are added as new columns and missing columns get their default.
        """
        # If there are no columns defined, initialize them from row_data keys.
        if not self.columns:
            for key, value in row_data.items():
                self.add_column(key)
            new_row = [row_data.get(col["id"], None) for col in self.columns]
        else:
            # For any new keys in row_data not in self.columns, add them.
            for key in row_data.keys():
                if not any(col["id"] == key for col in self.columns):
                    self.add_column(key)
            # Build the new row using provided values or each column’s default.
            new_row = [row_data.get(col["id"], col["default"]) for col in self.columns]
        self.data_mapping.append(new_row)
        self.rows.append(new_row)

    def add_rows(self, row_datas: List[Dict[str, Any]]) -> None:
        for row in row_datas:
            self.add_row(row)

    def get_row(self, index: int) -> Dict[str, Any]:
        """Return a row by its index as a dictionary (column_name -> value)."""
        if index < 0 or index >= len(self.data_mapping):
            raise IndexError("Row index out of range.")
        row = self.data_mapping[index]
        return {col["id"]: value for col, value in zip(self.columns, row)}
    
    def update_row(self, index: int, row_data: Dict[str, Any]) -> None:
        """
        Update an existing row at the given index.

        Only the columns specified in row_data will be updated.
        New keys are added as new columns.
        """
        if index < 0 or index >= len(self.data_mapping):
            raise IndexError("Row index out of range.")
        
        row = self.data_mapping[index]
        for key, value in row_data.items():
            if not any(col["id"] == key for col in self.columns):
                # Add new column if it does not exist.
                self.add_column(key)
                # The new column is added to the end of each row; update its value for the current row.
                row[-1] = value
            else:
                # Update the existing column value.
                for i, col in enumerate(self.columns):
                    if col["id"] == key:
                        row[i] = value
                        break
        self.rows[index] = row

    def delete_row(self, index: int) -> None:
        """Delete a row using its index."""
        if index < 0 or index >= len(self.data_mapping):
            raise IndexError("Row index out of range.")
        self.data_mapping.pop(index)
        self.rows.pop(index)

    def get_all_rows(self) -> List[Dict[str, Any]]:
        """Return all rows as a list of dictionaries."""
        return [dict(zip([col["id"] for col in self.columns], row)) for row in self.data_mapping]

# --- Seed Functions ---

def seed_columns() -> List[Dict[str, Any]]:
    """
    Seed initial columns.  
    You can mark a column as raw by including "raw": True.
    """
    columns = [
        {"id": "id", "default": None},
        {"id": "value", "default": None},
        {"id": "progress", "default": 0},
        # This column is flagged as raw, so any HTML inserted will be rendered as HTML.
        {"id": "raw_html", "default": "", "raw": True}
    ]
    return columns

def seed_rows(columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Seed 300 rows.
    Each row gets a unique 'id', an initial 'progress' of 0, and one cell per seeded column.
    """
    table_rows = []
    for i in range(300):
        row_uuid = str(uuid.uuid4())
        row = {"id": row_uuid, "progress": 0}
        for col in columns:
            # For demonstration, we fill the cell with the column's id.
            # (Except for the raw_html column, which we leave empty.)
            if col["id"] != "raw_html":
                row[col["id"]] = col["id"]
        table_rows.append(row)
    return table_rows

# --- Example Usage ---

if __name__ == "__main__":
    table = TableStateContainer()
    
    # Seed and add columns to the table.
    seed_cols = seed_columns()
    for col in seed_cols:
        table.add_column(col["id"], default=col.get("default", None), raw=col.get("raw", False))
    
    # Seed and add rows to the table.
    rows = seed_rows(seed_cols)
    table.add_rows(rows)
    
    # Example: Add a new row with a raw HTML field.
    table.add_row({
        "id": "manual-row",
        "progress": 100,
        "value": "Some text",
        "raw_html": "<strong>This is bold HTML!</strong>"
    })
    
    print("Initial table (first 2 rows):")
    for row in table.get_all_rows()[:2]:
        pprint(row)
