from app import app, db, Usuario
from werkzeug.security import generate_password_hash

with app.app_context():
    db.session.add(Usuario(
        nombre="admin",
        password=generate_password_hash("admin123"),
        rol="admin"
    ))

    db.session.add(Usuario(
        nombre="Juan Gonzales",
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