from flask import session


def iniciar(nombre, rol):
    session["usuario"] = nombre
    session["rol"] = rol


def cerrar():
    session.clear()


def hay_sesion():
    return "usuario" in session


def usuario_actual():
    return session.get("usuario")


def rol_actual():
    return session.get("rol")
