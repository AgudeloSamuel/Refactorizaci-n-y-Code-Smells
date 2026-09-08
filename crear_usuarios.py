from app import app

# Import compatible con todas las versiones:
# - Hasta v12: db y Usuario viven en app.py
# - Desde v13: db y Usuario viven en models.py
try:
    from models import db, Usuario
except ImportError:
    from app import db, Usuario

from werkzeug.security import generate_password_hash

with app.app_context():
    db.session.add(Usuario(
        nombre="admin",
        password=generate_password_hash("admin123"),
        rol="admin"
    ))

    db.session.add(Usuario(
        nombre="Juan Gomez",
        password=generate_password_hash("1234"),
        rol="profesor"
    ))

    db.session.add(Usuario(
        nombre="Pedro Sanchez",
        password=generate_password_hash("0000"),
        rol="estudiante"
    ))

    db.session.commit()

print("Usuarios creados correctamente")
