"""
generate_data.py — SIA3002C
Generador de datos sintéticos de estudiantes para entrenamiento y demostración.
Metodología documentada en: metodologia_datos_sinteticos.md
"""
import random
import numpy as np
import django
import os

# Asegurar que Django esté configurado si se corre directamente
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sia3002c.settings')

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# ──────────────────────────────────────────
# PARÁMETROS DE GENERACIÓN BASE
# ──────────────────────────────────────────
MATERIAS = [
    'Matemáticas', 'Español', 'Historia', 'Física',
    'Química', 'Inglés', 'Biología', 'Educación Física'
]
TOTAL_CLASES_POR_PERIODO = 80

NOMBRES = [
    "Alejandro García", "María López", "Carlos Hernández", "Ana Martínez",
    "José Ramírez", "Sofía González", "Luis Torres", "Laura Sánchez",
    "Pedro Flores", "Isabella Díaz", "Miguel Reyes", "Valentina Morales",
    "Andrés Jiménez", "Camila Ruiz", "Fernando Castro", "Daniela Vargas",
    "Roberto Ortiz", "Paulina Moreno", "Eduardo Guerrero", "Natalia Mendoza",
    "Ricardo Pérez", "Gabriela Aguilar", "Marco Vega", "Diana Cruz",
    "Alejandra Ríos", "Javier Navarro", "Verónica Castillo", "Diego Herrera",
    "Patricia Núñez", "Rodrigo Romero", "Fabiola Salinas", "Ernesto Ibarra",
    "Mónica Delgado", "César Guzmán", "Adriana Aceves", "Manuel Lara"
]


def generar_curp_sintetico(idx):
    """Genera una CURP sintética aleatoria y visualmente distinta."""
    import string
    letras_ini = ''.join(random.choices(string.ascii_uppercase, k=4))
    fecha_fake = f"{random.randint(0,9)}{random.randint(0,9)}{random.randint(1,12):02d}{random.randint(1,28):02d}"
    letras_fin = ''.join(random.choices(string.ascii_uppercase, k=6))
    digitos_fin = f"{random.randint(0,99):02d}"
    return f"{letras_ini}{fecha_fake}{letras_fin}{digitos_fin}"


def calcular_nivel_riesgo(pct_asistencia, materias_reprobadas, promedio, ingreso_norm,
                          sin_internet, distancia_alta):
    """
    Calcula el score de riesgo y nivel usando los pesos del documento de propuesta.
    Retorna: (probabilidad_float, nivel_str)
    """
    score = (
        0.35 * (1 - pct_asistencia / 100) +
        0.25 * (materias_reprobadas / len(MATERIAS)) +
        0.20 * (1 - promedio / 10) +
        0.12 * ingreso_norm +
        0.05 * sin_internet +
        0.03 * distancia_alta
    )
    # Ruido para variabilidad realista
    score += np.random.normal(0, 0.02)
    score = max(0, min(1, score))
    
    # Función sigmoide
    prob = 1 / (1 + np.exp(-5.0 * (score - 0.5)))
    
    # Clasificación
    if prob >= 0.70:
        nivel = 'ALTO'
    elif prob >= 0.40:
        nivel = 'MEDIO'
    else:
        nivel = 'BAJO'
    
    return round(prob, 4), nivel


def calcular_shap_valores(pct_asistencia, materias_reprobadas, promedio, ingreso_norm,
                           sin_internet, distancia_alta):
    """
    Calcula valores SHAP aproximados (para demo sin modelo entrenado).
    En producción, estos vienen del modelo XGBoost real.
    """
    shap_values = {
        'pct_asistencia': round(-0.35 * (pct_asistencia / 100 - 0.82), 4),
        'materias_reprobadas': round(0.25 * (materias_reprobadas / len(MATERIAS) - 0.15), 4),
        'promedio': round(-0.20 * (promedio / 10 - 0.72), 4),
        'ingreso_familiar': round(-0.12 * (0.5 - ingreso_norm), 4),
        'acceso_internet': round(0.05 * sin_internet, 4),
        'distancia_escuela': round(0.03 * distancia_alta, 4),
    }
    return shap_values


def generar_y_cargar_datos(modo='actual'):
    """
    Función principal: genera todos los datos sintéticos y los guarda.
    modo='historico': Genera data antigua (2023-2025) con predicciones para entrenar.
    modo='actual': Genera nueva generación ruidosa (2026-2027) sin predicciones pre-cargadas.
    """
    django.setup()
    
    from alumnos.models import Escuela, Grupo, Periodo, Alumno, Calificacion, Asistencia
    from prediccion.models import Prediccion
    from django.conf import settings
    
    seed = getattr(settings, 'RANDOM_SEED', RANDOM_SEED)
    random.seed(seed)
    np.random.seed(seed)
    
    # ── Configuración según Modo ───────────────────────────
    if modo == 'historico':
        print("Limpiando TODOS los datos escolares anteriores (Reinicio total)...")
        Escuela.objects.all().delete()
        Alumno.objects.all().delete()
        
        ciclos_a_generar = ['2023-2024', '2024-2025', '2025-2026']
        alumnos_por_ciclo = 500
        n_grupos = 5
        generar_prediccion = True
    else:
        print("Limpiando solo datos de la generación actual (2026-2027)...")
        # Borrar periodo o grupos 2026-2027 para poder regnerarlos sin afectar historiales
        Grupo.objects.filter(ciclo_escolar='2026-2027').delete()
        # Quedarán alumnos huerfanos que también borraremos
        Alumno.objects.filter(grupo__isnull=True).delete()
        
        ciclos_a_generar = ['2026-2027']
        alumnos_por_ciclo = 500
        n_grupos = 5
        generar_prediccion = False

    registros_totales = 0
    
    # ── 1. Escuela ──────────────────────────────────
    escuela, _ = Escuela.objects.get_or_create(
        nombre='Bachillerato Técnico No. 1 (DEMO)',
        defaults={
            'cct': 'DEM0001',
            'municipio': 'Ciudad de México',
            'estado': 'CDMX'
        }
    )

    for ciclo_actual in ciclos_a_generar:
        # Extraer el año inicial del ciclo para la fecha (ej. '2023-2024' -> 2023)
        year_inicio = int(ciclo_actual.split('-')[0])
        
        periodos_datos = [
            {'nombre': 'Parcial 1', 'inicio': f'{year_inicio}-09-01', 'fin': f'{year_inicio}-10-31'},
            {'nombre': 'Parcial 2', 'inicio': f'{year_inicio}-11-01', 'fin': f'{year_inicio}-12-20'},
            {'nombre': 'Parcial 3', 'inicio': f'{year_inicio + 1}-01-15', 'fin': f'{year_inicio + 1}-03-14'},
        ]
        
        # ── 2. Periodos ─────────────────────────────────
        periodos_obj = []
        for p in periodos_datos:
            periodo, _ = Periodo.objects.get_or_create(
                nombre=p['nombre'],
                ciclo_escolar=ciclo_actual,
                defaults={
                    'fecha_inicio': p['inicio'],
                    'fecha_fin': p['fin']
                }
            )
            periodos_obj.append(periodo)
        
        # ── 3. Grupos ────────────────────────────────────
        grupos_config = [
            {'nombre': '1° A Matutino', 'grado': 1, 'turno': 'Matutino'},
            {'nombre': '1° B Matutino', 'grado': 1, 'turno': 'Matutino'},
            {'nombre': '2° A Vespertino', 'grado': 2, 'turno': 'Vespertino'},
            {'nombre': '2° B Matutino', 'grado': 2, 'turno': 'Matutino'},
            {'nombre': '3° A Matutino', 'grado': 3, 'turno': 'Matutino'},
        ]
        grupos_obj = []
        for g in grupos_config:
            grupo, _ = Grupo.objects.get_or_create(
                nombre=g['nombre'],
                escuela=escuela,
                ciclo_escolar=ciclo_actual,
                defaults={
                    'grado': g['grado'],
                    'turno': g['turno']
                }
            )
            grupos_obj.append(grupo)

        # ── 4. Alumnos ───────────────────────────────────
        alumnos_por_grupo = alumnos_por_ciclo // n_grupos

        for grupo_idx, grupo in enumerate(grupos_obj):
            for i in range(alumnos_por_grupo):
                alumno_idx = grupo_idx * alumnos_por_grupo + i
            
                # Características socioeconómicas
                ingreso = np.random.lognormal(mean=9.2, sigma=0.6)
                ingreso = max(2000, min(60000, ingreso))
                ingreso_norm = 1 - (ingreso - 2000) / (60000 - 2000)  # 0=rico, 1=pobre
            
                becado = random.random() < (0.6 if ingreso < 8000 else 0.2)
                distancia = np.random.exponential(5)
                distancia = max(0.5, min(50, distancia))
                distancia_alta = 1.0 if distancia > 10 else 0.0
            
                sin_internet = 0.0 if random.random() < (0.71 - 0.3 * ingreso_norm) else 1.0
                acceso_internet = sin_internet == 0.0
            
                nivel_padre = random.choices(
                    ['Sin', 'Primaria', 'Secundaria', 'Bachillerato', 'Superior'],
                    weights=[0.15, 0.20, 0.30, 0.25, 0.10]
                )[0]
                nivel_madre = random.choices(
                    ['Sin', 'Primaria', 'Secundaria', 'Bachillerato', 'Superior'],
                    weights=[0.10, 0.18, 0.32, 0.28, 0.12]
                )[0]
                genero = random.choices(['M', 'F'], weights=[0.48, 0.52])[0]
            
                apellido1 = random.randint(10, 999)
                apellido2 = random.randint(10, 999)
                nombre = f"Persona {apellido1} {apellido2}"
            
                alumno, created = Alumno.objects.get_or_create(
                    curp=generar_curp_sintetico(alumno_idx),
                    defaults={
                        'grupo': grupo,
                        'nombre': nombre,
                        'genero': genero,
                        'ingreso_familiar': round(ingreso, 2),
                        'becado': becado,
                        'distancia_escuela_km': round(distancia, 2),
                        'nivel_estudios_padre': nivel_padre,
                        'nivel_estudios_madre': nivel_madre,
                        'acceso_internet': acceso_internet,
                        'activo': True
                    }
                )
                if created:
                    registros_totales += 1
            
                # ── 5. Calificaciones y Asistencias por Periodo ──
                for periodo in periodos_obj:
                    # Determinar si este alumno es "de riesgo" o no
                    # ~25% de alumnos serán de riesgo
                    es_riesgo = (ingreso_norm > 0.6 and not acceso_internet) or \
                               (distancia_alta and random.random() < 0.5) or \
                               random.random() < 0.10
                
                    # Asistencia con mayor solapamiento orgánico
                    if es_riesgo:
                        pct_asistencia = np.clip(
                            np.random.beta(4, 3) * 100, 30, 90
                        )
                    else:
                        pct_asistencia = np.clip(
                            np.random.beta(7, 2) * 100, 60, 100
                        )
                
                    clases_asistidas = int(TOTAL_CLASES_POR_PERIODO * pct_asistencia / 100)
                
                    Asistencia.objects.get_or_create(
                        alumno=alumno,
                        periodo=periodo,
                        defaults={
                            'total_clases': TOTAL_CLASES_POR_PERIODO,
                            'clases_asistidas': clases_asistidas
                        }
                    )
                
                    # Calificaciones por materia
                    materias_reprobadas = 0
                    calificaciones_valores = []
                
                    for materia in MATERIAS:
                        if es_riesgo:
                            # Distribución de calificaciones para alumnos en riesgo (promedio bajo, pero con posibilidad de aprobar)
                            cal = np.clip(np.random.normal(5.0, 2.0), 0, 10)
                        else:
                            # Distribución de calificaciones para alumnos regulares (promedio alto, pero con posibilidad de reprobar)
                            cal = np.clip(np.random.normal(8.0, 1.5), 4, 10)
                    
                        cal = round(cal, 1)
                        if cal < 6:
                            materias_reprobadas += 1
                        calificaciones_valores.append(cal)
                    
                        Calificacion.objects.get_or_create(
                            alumno=alumno,
                            periodo=periodo,
                            materia=materia,
                            defaults={'calificacion': cal}
                        )
                
                    promedio = sum(calificaciones_valores) / len(calificaciones_valores)
                
                    # ── 6. Predicción e Historial ──────────────────
                    if generar_prediccion:
                        prob, nivel = calcular_nivel_riesgo(
                            pct_asistencia, materias_reprobadas, promedio,
                            ingreso_norm, sin_internet, distancia_alta
                        )
                        # Removemos el "voltear etiquetas al azar", la incerteza ya viene del solapamiento orgánico
                        # de las distribuciones Beta y Normal de arriba.
                    
                        shap_vals = calcular_shap_valores(
                            pct_asistencia, materias_reprobadas, promedio,
                            ingreso_norm, sin_internet, distancia_alta
                        )
                    
                        Prediccion.objects.get_or_create(
                            alumno=alumno,
                            periodo=periodo,
                            defaults={
                                'nivel_riesgo': nivel,
                                'probabilidad_desercion': prob,
                                'factores_shap': shap_vals,
                                'modelo_version': '1.0.0-historical'
                            }
                        )
                        registros_totales += 3
                    else:
                        registros_totales += 2  # Solo asistencia + calificaciones
    
    print(f"✅ Datos sintéticos generados: {registros_totales} registros")
    return registros_totales


if __name__ == '__main__':
    total = generar_y_cargar_datos()
    print(f"Total de registros creados: {total}")
