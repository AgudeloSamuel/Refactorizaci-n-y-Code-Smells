from datetime import datetime, time

# Límites horarios de cada jornada
INICIO_DIURNA = time(5, 0)
FIN_DIURNA = time(16, 0)
INICIO_NOCTURNA = time(16, 0)
FIN_NOCTURNA = time(23, 59)


def a_hora(texto):
    """Convierte un texto 'HH:MM' en un objeto time."""
    return datetime.strptime(texto, "%H:%M").time()


def validar_jornada(jornada, inicio, fin):
    if jornada == "Diurna":
        return INICIO_DIURNA <= inicio <= FIN_DIURNA and INICIO_DIURNA <= fin <= FIN_DIURNA
    elif jornada == "Nocturna":
        return INICIO_NOCTURNA <= inicio <= FIN_NOCTURNA and INICIO_NOCTURNA <= fin <= FIN_NOCTURNA
    return False


def hay_solapamiento(inicio_nuevo, fin_nuevo, registros, excluir_id=None):
    """Devuelve True si el rango [inicio_nuevo, fin_nuevo) choca con algun registro."""
    return any(
        h.choca_con(inicio_nuevo, fin_nuevo)
        for h in registros
        if h.id != excluir_id
    )


def validar_horario(datos, inicio_nuevo, fin_nuevo, excluir_id=None):
    """Devuelve un mensaje de error si el horario no es valido, o None si es valido."""
    from models import Horario
    if inicio_nuevo >= fin_nuevo:
        return "Hora inválida"

    if not validar_jornada(datos.jornada, inicio_nuevo, fin_nuevo):
        return "Horario fuera de la jornada"

    salon_ocupado = Horario.query.filter_by(salon=datos.salon, dia=datos.dia).all()
    if hay_solapamiento(inicio_nuevo, fin_nuevo, salon_ocupado, excluir_id):
        return "El salón ya está ocupado en ese horario"

    profesor_ocupado = Horario.query.filter_by(profesor=datos.profesor, dia=datos.dia).all()
    if hay_solapamiento(inicio_nuevo, fin_nuevo, profesor_ocupado, excluir_id):
        return "El profesor ya tiene clase en ese horario"

    return None
