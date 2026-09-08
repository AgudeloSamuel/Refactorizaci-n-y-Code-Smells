from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, time
import os

app = Flask(__name__)
app.secret_key = "clave_secreta"

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'horarios.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ================== MODELOS ==================

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

with app.app_context():
    db.create_all()

# ================== LOGIN ==================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre = request.form["nombre"]
        password = request.form["password"]

        usuario = Usuario.query.filter_by(nombre=nombre).first()

        if usuario and check_password_hash(usuario.password, password):
            session["usuario"] = usuario.nombre
            session["rol"] = usuario.rol
            return redirect("/")
        else:
            flash("Usuario o contraseña incorrectos", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ================== VALIDACIONES ==================

def hay_solapamiento(inicio_nuevo, fin_nuevo, registros, excluir_id=None):
    """Devuelve True si el rango [inicio_nuevo, fin_nuevo) choca con algun registro."""
    for h in registros:
        if excluir_id is not None and h.id == excluir_id:
            continue
        ini = datetime.strptime(h.inicio, "%H:%M").time()
        fin_h = datetime.strptime(h.fin, "%H:%M").time()
        if inicio_nuevo < fin_h and fin_nuevo > ini:
            return True
    return False

def validar_jornada(jornada, inicio, fin):
    if jornada == "Diurna":
        return time(5,0) <= inicio <= time(16,0) and time(5,0) <= fin <= time(16,0)
    elif jornada == "Nocturna":
        return time(16,0) <= inicio <= time(23,59) and time(16,0) <= fin <= time(23,59)
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

# ================== INDEX ==================

@app.route("/")
def index():
    if "usuario" not in session:
        return redirect("/login")

    rol = session["rol"]
    usuario = session["usuario"]
    busqueda = request.args.get("busqueda")

    if rol == "profesor":
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

# ================== AGREGAR ==================

@app.route("/agregar", methods=["POST"])
def agregar():
    if session.get("rol") != "admin":
        flash("No autorizado", "error")
        return redirect("/")

    profesor = request.form["profesor"]
    materia = request.form["materia"]
    dia = request.form["dia"]
    inicio = request.form["inicio"]
    fin = request.form["fin"]
    salon = request.form["salon"]
    jornada = request.form["jornada"]

    inicio_nuevo = datetime.strptime(inicio, "%H:%M").time()
    fin_nuevo = datetime.strptime(fin, "%H:%M").time()

    error = validar_horario(profesor, dia, salon, jornada, inicio_nuevo, fin_nuevo)
    if error:
        flash(error, "error")
        return redirect("/")

    nuevo = Horario(
        profesor=profesor,
        materia=materia,
        dia=dia,
        inicio=inicio,
        fin=fin,
        salon=salon,
        jornada=jornada
    )

    db.session.add(nuevo)
    db.session.commit()

    flash("Horario agregado correctamente", "success")
    return redirect("/")

# ================== EDITAR ==================

@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    if "usuario" not in session:
        return redirect("/login")

    horario = Horario.query.get_or_404(id)

    if session["rol"] == "estudiante":
        flash("No autorizado", "error")
        return redirect("/")

    if session["rol"] == "profesor" and horario.profesor != session["usuario"]:
        flash("No autorizado", "error")
        return redirect("/")

    if request.method == "POST":
        materia = request.form["materia"]
        dia = request.form["dia"]
        inicio = request.form["inicio"]
        fin = request.form["fin"]
        salon = request.form["salon"]
        jornada = request.form["jornada"]

        inicio_nuevo = datetime.strptime(inicio, "%H:%M").time()
        fin_nuevo = datetime.strptime(fin, "%H:%M").time()

        if inicio_nuevo >= fin_nuevo:
            flash("Hora inválida", "error")
            return redirect(f"/editar/{id}")

        if not validar_jornada(jornada, inicio_nuevo, fin_nuevo):
            flash("Horario fuera de la jornada", "error")
            return redirect(f"/editar/{id}")

        salon_ocupado = Horario.query.filter_by(salon=salon, dia=dia).all()
        if hay_solapamiento(inicio_nuevo, fin_nuevo, salon_ocupado, excluir_id=horario.id):
            flash("El salón ya está ocupado", "error")
            return redirect(f"/editar/{id}")

        profesor_ocupado = Horario.query.filter_by(profesor=horario.profesor, dia=dia).all()
        if hay_solapamiento(inicio_nuevo, fin_nuevo, profesor_ocupado, excluir_id=horario.id):
            flash("El profesor ya tiene clase en ese horario", "error")
            return redirect(f"/editar/{id}")

        horario.materia = materia
        horario.dia = dia
        horario.inicio = inicio
        horario.fin = fin
        horario.salon = salon
        horario.jornada = jornada

        db.session.commit()
        flash("Horario actualizado", "success")
        return redirect("/")

    return render_template("editar.html", horario=horario, rol=session["rol"])

# ================== ELIMINAR ==================

@app.route("/eliminar/<int:id>", methods=["POST"])
def eliminar(id):
    if session.get("rol") != "admin":
        flash("No autorizado", "error")
        return redirect("/")

    horario = Horario.query.get_or_404(id)
    db.session.delete(horario)
    db.session.commit()

    flash("Horario eliminado", "success")
    return redirect("/")

# ================== RUN ==================

if __name__ == "__main__":
    app.run(debug=True)
