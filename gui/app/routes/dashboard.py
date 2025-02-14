from flask import render_template, g
from models.user import User

def index():
    user = User()
    # Directly use g; the table must have been loaded for this request.
    print(g.get('table'))  # For debugging
    return render_template("dashboard.j2", table=g.get('table'), user=user)
