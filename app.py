from flask import Flask, render_template, request, redirect, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

import sesion
from models import db, Usuario, Horario, DatosHorario
from validaciones import a_hora, validar_horario

app = Flask(__name__)
app.secret_key = "clave_secreta"

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'horarios.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# Roles del sistema
ROL_ADMIN = "admin"
ROL_PROFESOR = "profesor"
ROL_ESTUDIANTE = "estudiante"


def requiere_rol(rol_requerido):
    """Restringe el acceso a la ruta a un rol concreto."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if sesion.rol_actual() != rol_requerido:
                flash("No autorizado", "error")
                return redirect("/")
            return vista(*args, **kwargs)
        return envoltura
    return decorador


def credenciales_validas(usuario, password):
    """Verifica que el usuario exista y la contraseña coincida."""
    return usuario is not None and check_password_hash(usuario.password, password)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre = request.form["nombre"]
        password = request.form["password"]

        usuario = Usuario.query.filter_by(nombre=nombre).first()

        if credenciales_validas(usuario, password):
            sesion.iniciar(usuario.nombre, usuario.rol)
            return redirect("/")

        flash("Usuario o contraseña incorrectos", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    sesion.cerrar()
    return redirect("/login")


def aplicar_busqueda(query, busqueda):
    """Aplica el filtro de busqueda por id, profesor o materia."""
    if not busqueda:
        return query

    filtros = (
        Horario.profesor.ilike(f"%{busqueda}%") |
        Horario.materia.ilike(f"%{busqueda}%")
    )
    if busqueda.isdigit():
        filtros = (Horario.id == int(busqueda)) | filtros

    return query.filter(filtros)


@app.route("/")
def index():
    if not sesion.hay_sesion():
        return redirect("/login")

    rol = sesion.rol_actual()
    usuario = sesion.usuario_actual()

    if rol == ROL_PROFESOR:
        query = Horario.query.filter_by(profesor=usuario)
    else:
        query = Horario.query

    query = aplicar_busqueda(query, request.args.get("busqueda"))

    horarios = query.all()
    return render_template("index.html", horarios=horarios, rol=rol)


@app.route("/agregar", methods=["POST"])
@requiere_rol(ROL_ADMIN)
def agregar():
    datos = DatosHorario.desde_formulario(request.form)

    inicio_nuevo = a_hora(datos.inicio)
    fin_nuevo = a_hora(datos.fin)

    error = validar_horario(datos, inicio_nuevo, fin_nuevo)
    if error:
        flash(error, "error")
        return redirect("/")

    nuevo = Horario(
        profesor=datos.profesor,
        materia=datos.materia,
        dia=datos.dia,
        inicio=datos.inicio,
        fin=datos.fin,
        salon=datos.salon,
        jornada=datos.jornada
    )

    db.session.add(nuevo)
    db.session.commit()

    flash("Horario agregado correctamente", "success")
    return redirect("/")


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    if not sesion.hay_sesion():
        return redirect("/login")

    horario = Horario.query.get_or_404(id)

    if sesion.rol_actual() == ROL_ESTUDIANTE:
        flash("No autorizado", "error")
        return redirect("/")

    if sesion.rol_actual() == ROL_PROFESOR and horario.profesor != sesion.usuario_actual():
        flash("No autorizado", "error")
        return redirect("/")

    if request.method == "POST":
        datos = DatosHorario.desde_formulario(request.form, profesor=horario.profesor)

        inicio_nuevo = a_hora(datos.inicio)
        fin_nuevo = a_hora(datos.fin)

        error = validar_horario(datos, inicio_nuevo, fin_nuevo, excluir_id=horario.id)
        if error:
            flash(error, "error")
            return redirect(f"/editar/{id}")

        horario.materia = datos.materia
        horario.dia = datos.dia
        horario.inicio = datos.inicio
        horario.fin = datos.fin
        horario.salon = datos.salon
        horario.jornada = datos.jornada

        db.session.commit()
        flash("Horario actualizado", "success")
        return redirect("/")

    return render_template("editar.html", horario=horario, rol=sesion.rol_actual())


@app.route("/eliminar/<int:id>", methods=["POST"])
@requiere_rol(ROL_ADMIN)
def eliminar(id):
    horario = Horario.query.get_or_404(id)
    db.session.delete(horario)
    db.session.commit()

    flash("Horario eliminado", "success")
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
