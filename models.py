from flask_sqlalchemy import SQLAlchemy
from validaciones import a_hora

db = SQLAlchemy()


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
