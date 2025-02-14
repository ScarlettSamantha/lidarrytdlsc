from flask import render_template, g
from models.user import User

def index():
    user = User()
    return render_template("dashboard.j2", table=g.get('table'), user=user)
