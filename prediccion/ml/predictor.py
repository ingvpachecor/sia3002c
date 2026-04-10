"""
predictor.py — SIA3002C
Servicio de predicción batch usando el modelo XGBoost entrenado + SHAP.
"""
import os
import pickle
import numpy as np
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sia3002c.settings')


def _cargar_modelo():
    """Carga el modelo XGBoost, scaler y lista de features desde disco."""
    from django.conf import settings
    models_dir = Path(settings.ML_MODELS_DIR)
    
    model_path = models_dir / 'modelo_xgboost.pkl'
    if not model_path.exists():
        raise FileNotFoundError(
            f"Modelo no encontrado en {model_path}. "
            "Ejecuta primero: python prediccion/ml/train_model.py"
        )
    
    with open(models_dir / 'modelo_xgboost.pkl', 'rb') as f:
        modelo = pickle.load(f)
    with open(models_dir / 'scaler.pkl', 'rb') as f:
        scaler = pickle.load(f)
    with open(models_dir / 'features.pkl', 'rb') as f:
        features = pickle.load(f)
    
    return modelo, scaler, features


def _extraer_features_alumno(alumno, periodo):
    """
    Extrae el vector de features para un alumno en un periodo dado.
    Returns: dict con las variables del modelo
    """
    from alumnos.models import Calificacion, Asistencia

    # Calificaciones del periodo
    cals = Calificacion.objects.filter(alumno=alumno, periodo=periodo)
    if cals.exists():
        calificaciones = [float(c.calificacion) for c in cals]
        promedio = sum(calificaciones) / len(calificaciones)
        materias_reprobadas = sum(1 for c in calificaciones if c < 6)
    else:
        promedio = 7.0
        materias_reprobadas = 0
    
    # Asistencia del periodo
    try:
        asistencia = Asistencia.objects.get(alumno=alumno, periodo=periodo)
        pct_asistencia = float(asistencia.porcentaje_asistencia)
    except Asistencia.DoesNotExist:
        pct_asistencia = 85.0
    
    # Variables socioeconómicas
    nivel_map = {'Sin': 0, 'Primaria': 1, 'Secundaria': 2, 'Bachillerato': 3, 'Superior': 4}
    
    return {
        'promedio': promedio,
        'materias_reprobadas': materias_reprobadas,
        'pct_asistencia': pct_asistencia,
        'ingreso_familiar': float(alumno.ingreso_familiar or 8000),
        'becado': int(alumno.becado),
        'distancia_escuela_km': float(alumno.distancia_escuela_km or 5.0),
        'nivel_estudios_padre': nivel_map.get(alumno.nivel_estudios_padre or 'Secundaria', 2),
        'nivel_estudios_madre': nivel_map.get(alumno.nivel_estudios_madre or 'Secundaria', 2),
        'acceso_internet': int(alumno.acceso_internet),
    }


def _calcular_shap(modelo, scaler, features, X_scaled):
    """Calcula los valores SHAP para el vector de features."""
    try:
        import shap
        explainer = shap.TreeExplainer(modelo)
        shap_values = explainer.shap_values(X_scaled)
        
        # Para clasificación binaria, tomar la clase positiva (≥ 0.5)
        if isinstance(shap_values, list):
            shap_vals = shap_values[1][0]
        else:
            shap_vals = shap_values[0]
        
        return dict(zip(features, [round(float(v), 4) for v in shap_vals]))
    except Exception:
        # Fallback: usar feature importances del modelo
        importances = modelo.feature_importances_
        return dict(zip(features, [round(float(v), 4) for v in importances]))


def predecir_alumno(alumno, periodo):
    """
    Predice el nivel de riesgo de deserción para un alumno en un periodo.
    
    Returns: dict con nivel_riesgo, probabilidad y factores_shap
    """
    from django.conf import settings
    
    modelo, scaler, features = _cargar_modelo()
    features_dict = _extraer_features_alumno(alumno, periodo)
    
    # Vector de features ordenado
    X = np.array([[features_dict[f] for f in features]])
    X_scaled = scaler.transform(X)
    
    prob = float(modelo.predict_proba(X_scaled)[0][1])
    
    # Clasificación por umbrales
    if prob >= 0.70:
        nivel = 'ALTO'
    elif prob >= 0.40:
        nivel = 'MEDIO'
    else:
        nivel = 'BAJO'
    
    shap_vals = _calcular_shap(modelo, scaler, features, X_scaled)
    version = getattr(settings, 'MODEL_VERSION', '1.0.0')
    
    return {
        'nivel_riesgo': nivel,
        'probabilidad_desercion': round(prob, 4),
        'factores_shap': shap_vals,
        'modelo_version': version,
    }


def ejecutar_prediccion_batch(periodo):
    """
    Ejecuta predicciones para todos los alumnos activos en un periodo.
    Guarda/actualiza las predicciones en la base de datos.
    
    Returns: dict con conteo de resultados
    """
    from alumnos.models import Alumno
    from prediccion.models import Prediccion
    
    alumnos = Alumno.objects.filter(activo=True)
    procesados = 0
    errores = 0
    
    for alumno in alumnos:
        try:
            resultado = predecir_alumno(alumno, periodo)
            
            Prediccion.objects.update_or_create(
                alumno=alumno,
                periodo=periodo,
                defaults=resultado
            )
            procesados += 1
        except Exception as e:
            print(f"Error en alumno {alumno.nombre}: {e}")
            errores += 1
    
    return {
        'procesados': procesados,
        'errores': errores,
        'periodo': str(periodo),
    }
