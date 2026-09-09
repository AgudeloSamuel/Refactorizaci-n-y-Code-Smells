from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, time
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = "clave_secreta"

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'horarios.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Límites horarios de cada jornada
INICIO_DIURNA = time(5, 0)
FIN_DIURNA = time(16, 0)
INICIO_NOCTURNA = time(16, 0)
FIN_NOCTURNA = time(23, 59)

# Roles del sistema
ROL_ADMIN = "admin"
ROL_PROFESOR = "profesor"
ROL_ESTUDIANTE = "estudiante"


def requiere_rol(rol_requerido):
    """Restringe el acceso a la ruta a un rol concreto."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if session.get("rol") != rol_requerido:
                flash("No autorizado", "error")
                return redirect("/")
            return vista(*args, **kwargs)
        return envoltura
    return decorador

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), nullable=False)

class Horario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profesor = db.Column(db.String(100), nullable=False)
    materia = db.Column(db.String(100), nullable=False)
    dia = db.Column(db.String(50), nullable=False)
    inicio = db.Column(db.String(5), nullable=False)
    fin = db.Column(db.String(5), nullable=False)
    salon = db.Column(db.String(10), nullable=False)
    jornada = db.Column(db.String(10), nullable=False)

    def choca_con(self, inicio_nuevo, fin_nuevo):
        """Indica si este horario se solapa con el rango dado."""
        ini = a_hora(self.inicio)
        fin_h = a_hora(self.fin)
        return inicio_nuevo < fin_h and fin_nuevo > ini

class DatosHorario:
    """Agrupa los campos de un horario que siempre viajan juntos."""
    def __init__(self, profesor, materia, dia, inicio, fin, salon, jornada):
        self.profesor = profesor
        self.materia = materia
        self.dia = dia
        self.inicio = inicio
        self.fin = fin
        self.salon = salon
        self.jornada = jornada

    @classmethod
    def desde_formulario(cls, form, profesor=None):
        return cls(
            profesor=profesor if profesor is not None else form["profesor"],
            materia=form["materia"],
            dia=form["dia"],
            inicio=form["inicio"],
            fin=form["fin"],
            salon=form["salon"],
            jornada=form["jornada"],
        )

with app.app_context():
    db.create_all()

@app.route("/login", methods=["GET", "POST"])
def credenciales_validas(usuario, password):
    """Verifica que el usuario exista y la contraseña coincida."""
    return usuario is not None and check_password_hash(usuario.password, password)


def login():
    if request.method == "POST":
        nombre = request.form["nombre"]
        password = request.form["password"]

        usuario = Usuario.query.filter_by(nombre=nombre).first()

        if credenciales_validas(usuario, password):
            session["usuario"] = usuario.nombre
            session["rol"] = usuario.rol
            return redirect("/")

        flash("Usuario o contraseña incorrectos", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def a_hora(texto):
    """Convierte un texto 'HH:MM' en un objeto time."""
    return datetime.strptime(texto, "%H:%M").time()

def hay_solapamiento(inicio_nuevo, fin_nuevo, registros, excluir_id=None):
    """Devuelve True si el rango [inicio_nuevo, fin_nuevo) choca con algun registro."""
    return any(
        h.choca_con(inicio_nuevo, fin_nuevo)
        for h in registros
        if h.id != excluir_id
    )

def validar_jornada(jornada, inicio, fin):
    if jornada == "Diurna":
        return INICIO_DIURNA <= inicio <= FIN_DIURNA and INICIO_DIURNA <= fin <= FIN_DIURNA
    elif jornada == "Nocturna":
        return INICIO_NOCTURNA <= inicio <= FIN_NOCTURNA and INICIO_NOCTURNA <= fin <= FIN_NOCTURNA
    return False

def validar_horario(profesor, dia, salon, jornada, inicio_nuevo, fin_nuevo, excluir_id=None):
    """Devuelve un mensaje de error si el horario no es valido, o None si es valido."""
    if inicio_nuevo >= fin_nuevo:
        return "Hora inválida"

    if not validar_jornada(jornada, inicio_nuevo, fin_nuevo):
        return "Horario fuera de la jornada"

    salon_ocupado = Horario.query.filter_by(salon=salon, dia=dia).all()
    if hay_solapamiento(inicio_nuevo, fin_nuevo, salon_ocupado, excluir_id):
        return "El salón ya está ocupado en ese horario"

    profesor_ocupado = Horario.query.filter_by(profesor=profesor, dia=dia).all()
    if hay_solapamiento(inicio_nuevo, fin_nuevo, profesor_ocupado, excluir_id):
        return "El profesor ya tiene clase en ese horario"

    return None

@app.route("/")
def index():
    if "usuario" not in session:
        return redirect("/login")

    rol = session["rol"]
    usuario = session["usuario"]
    busqueda = request.args.get("busqueda")

    if rol == ROL_PROFESOR:
        query = Horario.query.filter_by(profesor=usuario)
    else:
        query = Horario.query

    if busqueda:
        if busqueda.isdigit():
            query = query.filter(
                (Horario.id == int(busqueda)) |
                (Horario.profesor.ilike(f"%{busqueda}%")) |
                (Horario.materia.ilike(f"%{busqueda}%"))
            )
        else:
            query = query.filter(
                (Horario.profesor.ilike(f"%{busqueda}%")) |
                (Horario.materia.ilike(f"%{busqueda}%"))
            )

    horarios = query.all()
    return render_template("index.html", horarios=horarios, rol=rol)

@app.route("/agregar", methods=["POST"])
@requiere_rol(ROL_ADMIN)
def agregar():
    datos = DatosHorario.desde_formulario(request.form)

    inicio_nuevo = a_hora(datos.inicio)
    fin_nuevo = a_hora(datos.fin)

    error = validar_horario(datos.profesor, datos.dia, datos.salon, datos.jornada, inicio_nuevo, fin_nuevo)
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
    if "usuario" not in session:
        return redirect("/login")

    horario = Horario.query.get_or_404(id)

    if session["rol"] == ROL_ESTUDIANTE:
        flash("No autorizado", "error")
        return redirect("/")

    if session["rol"] == ROL_PROFESOR and horario.profesor != session["usuario"]:
        flash("No autorizado", "error")
        return redirect("/")

    if request.method == "POST":
        datos = DatosHorario.desde_formulario(request.form, profesor=horario.profesor)

        inicio_nuevo = a_hora(datos.inicio)
        fin_nuevo = a_hora(datos.fin)

        error = validar_horario(
            datos.profesor, datos.dia, datos.salon, datos.jornada,
            inicio_nuevo, fin_nuevo, excluir_id=horario.id
        )
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

    return render_template("editar.html", horario=horario, rol=session["rol"])

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
