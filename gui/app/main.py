# main.py
# ruff: noqa: E402
# pyright: reportMissingImports=false
# This needs to be on top for event reasons.
import eventlet
eventlet.monkey_patch()

import time
from flask import Flask, g
from flask_socketio import SocketIO
from background.workers import background_thread
from state import TableStateContainer
from pprint import pprint
from todo_queue import todo_queue


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# Tell SocketIO to use eventlet
socketio = SocketIO(app, async_mode='eventlet')

def load_routes():
    from routes.dashboard import index
    from routes.profile import profile
    from routes.settings import settings

    app.add_url_rule("/", "dashboard", index, True)
    app.add_url_rule("/profile", "profile", profile, True)
    app.add_url_rule("/setting", "settings", settings)
    app.add_url_rule("/logout", "logout", settings)
    app.add_url_rule("/update_cell", "update_cell", settings)

def load_sockets(socketio):
    from ws.handle import register_sockets
    register_sockets(socketio=socketio)

def get_test_table() -> TableStateContainer:
    return TableStateContainer()

def create_table():
    from helpers.data_generation import seed_columns, seed_rows
    
    table = TableStateContainer()
    columns = seed_columns()
    rows = seed_rows()
    table.add_columns(columns)
    table.add_rows(rows)
    return table

# Store your table persistently in app.config
app.config['table'] = create_table()

@app.before_request
def load_table_into_g():
    # Copy the persistent table into g for each request.
    g.table = app.config.get('table')
    g.todo_queue = app.config.get('todo_queue')

def load_app_data():
    # Store the SocketIO instance in g if you want it there,
    # but note that g only lives during an application context.
    g.socketio = socketio
    app.config['todo_queue'] = todo_queue()


if __name__ == "__main__":
    # Push a persistent application context so that g is available.
    app_ctx = app.app_context()
    app_ctx.push()

    load_app_data()
    load_table_into_g()
    load_routes()
    load_sockets(socketio)

    @socketio.on("connect")
    def on_connect():
        print("Client connected.")



    # Pass the socketio instance and the table to the background thread
    socketio.start_background_task(background_thread, table=g.table, socketio=socketio)

    # Run the server with eventlet
    socketio.run(app, debug=True, host="127.0.0.1", port=5005, use_reloader=True)
