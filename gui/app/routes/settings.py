from flask import render_template

def settings():
    from main import get_test_table
    from models.user import User
    user = User()
    return render_template("dashboard.j2", table=get_test_table(), user=user)
