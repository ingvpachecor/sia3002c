import json
import requests
from django.conf import settings

FACTOR_LABELS = {
    'pct_asistencia': 'porcentaje de asistencia',
    'materias_reprobadas': 'materias reprobadas',
    'promedio': 'promedio de calificaciones',
    'ingreso_familiar': 'situación económica familiar',
    'acceso_internet': 'falta de acceso a internet en casa',
    'distancia_escuela': 'distancia al plantel escolar',
}


def _configurar_gemini():
    """Devuelve la API Key configurada."""
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key or api_key.startswith('COLOCA') or api_key.startswith('AIza') is False:
        raise ValueError(
            "La API key de Gemini no está configurada o es inválida. "
            "Revisa el archivo .env"
        )
    return api_key


def _llamar_api_gemini(prompt: str) -> str:
    """Ejecuta una llamada HTTP REST directa a la API de Google Gemini."""
    api_key = _configurar_gemini()
    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
    # Limpiar el nombre del modelo si incluyeron 'models/' por error
    if model_name.startswith('models/'):
        model_name = model_name[7:]
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    
    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {response.text}")
        
    data = response.json()
    try:
        return data['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError) as e:
        raise Exception(f"Respuesta inesperada de Gemini: {data}")


def _describir_factores_shap(factores_shap: dict, nivel_riesgo: str) -> str:
    """Convierte los valores SHAP en texto legible para el prompt del LLM."""
    if not factores_shap:
        return "No se dispone de factores de riesgo detallados."
    
    # Ordenar por valor absoluto descendente
    factores_ordenados = sorted(
        factores_shap.items(),
        key=lambda x: abs(x[1]),
        reverse=True
    )
    
    lineas = []
    for factor, valor in factores_ordenados[:4]:
        label = FACTOR_LABELS.get(factor, factor)
        direccion = "elevado" if valor > 0 else "favorable"
        lineas.append(f"  • {label.capitalize()}: impacto {direccion} ({valor:+.3f})")
    
    return "\n".join(lineas)


def generar_recomendacion_gemini(prediccion) -> str:
    """
    Genera una recomendación de intervención personalizada para un alumno.
    """
    alumno = prediccion.alumno
    
    factores_texto = _describir_factores_shap(
        prediccion.factores_shap,
        prediccion.nivel_riesgo
    )
    
    prompt = f"""Eres un orientador educativo experto en educación media superior (bachillerato) en México. 
Tu tarea es generar una recomendación de intervención concisa y práctica para el tutor o docente 
a cargo del siguiente alumno en riesgo de abandono escolar.

## Datos del alumno:
- **Nombre:** {alumno.nombre}
- **Grupo:** {alumno.grupo.nombre if alumno.grupo else 'No asignado'}
- **Nivel de riesgo de deserción:** {prediccion.nivel_riesgo} ({float(prediccion.probabilidad_desercion):.1%})
- **Periodo evaluado:** {prediccion.periodo.nombre}

## Factores de riesgo identificados por el modelo IA:
{factores_texto}

## Instrucciones:
Genera un plan de acción en el siguiente formato:

**Diagnóstico:** (1-2 oraciones explicando el riesgo en lenguaje claro para el docente)

**Acciones inmediatas (próximas 2 semanas):**
1. (acción específica y realizable)
2. (acción específica y realizable)
3. (acción específica y realizable)

**Seguimiento sugerido:** (frecuencia y tipo de seguimiento)

**Mensaje sugerido para los padres/tutores:** (párrafo breve, empático y no alarmista para comunicar la situación)

Usa lenguaje claro, empático y orientado a la acción. Evita tecnicismos."""

    try:
        return _llamar_api_gemini(prompt)
    except Exception as e:
        error_msg = f"⚠️ Error de la API de Google Gemini:\n{str(e)}\n\n(Asegúrate de que tu API Key y GEMINI_MODEL estén correctos en el archivo .env y hayas reiniciado la terminal)."
        print(error_msg)
        return error_msg


def generar_correo_padres(prediccion) -> str:
    """
    Genera un borrador de correo para los padres.
    """
    alumno = prediccion.alumno
    factores_texto = _describir_factores_shap(
        prediccion.factores_shap,
        prediccion.nivel_riesgo
    )
    
    prompt = f"""Redacta un correo electrónico formal pero empático de un orientador escolar 
para los padres o tutores del alumno {alumno.nombre}, quien presenta un nivel de riesgo 
{prediccion.nivel_riesgo} de abandono escolar según el sistema de análisis del plantel.

Factores que contribuyen al riesgo:
{factores_texto}

El correo debe:
- Ser respetuoso y no alarmista
- Invitar a una reunión con el tutor
- Ofrecer opciones de apoyo (becas, asesoría académica, etc.)
- Tener máximo 200 palabras
- Estar en español formal

Formato: Asunto: ... / Cuerpo del correo"""

    return _llamar_api_gemini(prompt)


def generar_recomendacion_demo(prediccion) -> str:
    """
    Genera una recomendación de demostración sin llamar a la API de Gemini.
    Útil cuando no hay API key configurada.
    """
    alumno = prediccion.alumno
    nivel = prediccion.nivel_riesgo
    prob = float(prediccion.probabilidad_desercion)
    
    # Obtener el factor más influyente
    factores = prediccion.factores_shap or {}
    factor_principal = max(factores, key=lambda k: abs(factores[k]), default='asistencia')
    label_principal = FACTOR_LABELS.get(factor_principal, factor_principal)
    
    return f"""**Diagnóstico:** El alumno {alumno.nombre} presenta un riesgo {nivel.lower()} de deserción escolar ({prob:.1%}), principalmente influenciado por su {label_principal}. Se requiere seguimiento personalizado.

**Acciones inmediatas (próximas 2 semanas):**
1. Reunión individual con el alumno para identificar obstáculos personales y académicos.
2. Contactar a los padres/tutores para informar sobre la situación e invitarlos a colaborar.
3. Revisar posibilidad de acceso a becas o apoyos educativos si hay factores económicos.

**Seguimiento sugerido:** Revisión semanal de asistencia y calificaciones durante el siguiente mes. Registro en bitácora de seguimiento del tutor.

**Mensaje sugerido para los padres/tutores:** Estimados padres de {alumno.nombre}, nos comunicamos para compartirles que hemos identificado algunos indicadores que requieren atención oportuna en el desempeño escolar de su hijo/a. Les invitamos a una reunión con el tutor para trabajar juntos en un plan de apoyo personalizado. Estamos comprometidos con el éxito educativo de {alumno.nombre}.

*(Nota: Esta recomendación es una demostración estática. Configure su API key de Google Gemini en el archivo .env para obtener recomendaciones personalizadas generadas por IA.)*"""
