import time
import random
import uuid
from state import TableStateContainer

def background_thread(table: TableStateContainer, socketio):
    while True:
        time.sleep(2)
        if not table.get_columns():
            continue
        row = random.choice(table.get_all_rows())
        row_id = random.choice([row['id'] for row in table.get_all_rows()])
        new_value = str(uuid.uuid4())
        row[row_id] = new_value
        socketio.emit("update_cell", {
            "row_id": row["id"],
            "column": 'progress',
            "new_value": random.randrange(1, 99)
        })