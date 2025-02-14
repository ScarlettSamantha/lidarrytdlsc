from typing import Any, Dict, List
import uuid
 
def seed_columns() -> List[Dict[str, Any]]:
    columns = [
        {"id": "id", "default": None},
        {"id": "value", "default": None},
        {"id": "progress", "default": 0}
    ]
    return columns


def seed_rows() -> List[Dict[str, Any]]:
    # Create 300 rows (tickets), each with an initial progress of 0.
    table_rows = []
    for i in range(300):
        row_uuid = str(uuid.uuid4())
        # Include a progress field (initially 0) along with other cells.
        row = {"id": row_uuid, "value": str(i), "progress": 0}
        table_rows.append(row)
    return table_rows
