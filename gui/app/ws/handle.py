# ws/handle.py
import time
from pprint import pprint
from typing import TYPE_CHECKING, Any
from flask import current_app, json, g
from flask_socketio import emit

if TYPE_CHECKING:
    from gui.app.todo_queue import todo_queue as TodoQueueType


def register_sockets(socketio):
    @socketio.on('export_selected_rows')
    def handle_export_select_rows(data):
        selected_ids = data.get('selected_id', [])
        action = data.get('action', '')
        print(f"[WS] export_selected_rows: selected_ids={selected_ids}, action={action}")
        todo_queue: TodoQueueType | Any = current_app.config.get('todo_queue')
        for id in selected_ids:
            todo_queue.items.append(id)
        pprint(todo_queue)
        # Emit with "ids" at top level
        emit('export_complete', {
            "ids": selected_ids
        })


    @socketio.on('add_column_request')
    def on_add_column_request(data):
        """
        Handle the request to add a new column.
        Expected data format: 
        { 
            column: {id: <column_id>, name: <column_name>}, 
            default_value: <default_value>
        }
        """
        column = data.get('column')
        default_value = data.get('default_value', '')
        print(f"[WS] add_column_request: column={column}, default_value={default_value}")

        table = current_app.config.get('table')
        if table:
            # Assume the table object has an add_columns method
            table.add_columns([column])
            # Broadcast the new column information to all clients.
            emit('add_column', {'column': column, 'default_value': default_value}, broadcast=True)
        else:
            emit('error_notification', {'message': 'Table not available in app config.'})


    @socketio.on('remove_column_request')
    def on_remove_column_request(data):
        """
        Handle the request to remove a column.
        Expected data format: { column_id: <id_of_column_to_remove> }
        """
        column_id = data.get('column_id')
        print(f"[WS] remove_column_request: column_id={column_id}")

        table = current_app.config.get('table')
        if table:
            # Ensure your table object implements a remove_column method.
            if hasattr(table, 'remove_column'):
                table.remove_column(column_id)
                # Broadcast the removal to all clients.
                emit('remove_column', {'column_id': column_id}, broadcast=True)
            else:
                emit('error_notification', {'message': 'remove_column method not implemented in table.'})
        else:
            emit('error_notification', {'message': 'Table not available in app config.'})


    @socketio.on('start_ticket')
    def handle_start_ticket(data):
        """
        Handle a ticket processing request.
        Expected data format: { ticket_id: <ticket_identifier> }
        Simulates processing by updating progress and then emitting a new row event.
        """
        ticket_id = data.get('ticket_id')
        print(f"[WS] start_ticket: ticket_id={ticket_id}")

        # Simulate some work by updating progress in steps.
        for progress in range(0, 101, 20):
            time.sleep(0.5)  # Simulate work delay
            emit('update_progress', {'uuid': ticket_id, 'progress': progress}, broadcast=True)
        
        # After processing, simulate adding a new row (e.g., a processed ticket record).
        new_row = {'id': ticket_id, 'status': 'processed', 'details': f'Ticket {ticket_id} processed.'}
        emit('new_row', {'row': new_row}, broadcast=True)