"""
Modelos de la app 'prediccion' — SIA3002C
Incluye: Prediccion, ArchivosCargados
"""
import uuid
from django.db import models
from alumnos.models import Alumno, Periodo, TimeStampedModel


class Prediccion(TimeStampedModel):
    NIVELES_RIESGO = [
        ('ALTO', 'Alto'),
        ('MEDIO', 'Medio'),
        ('BAJO', 'Bajo'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='predicciones')
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name='predicciones')
    nivel_riesgo = models.CharField(max_length=10, choices=NIVELES_RIESGO, verbose_name="Nivel de riesgo")
    probabilidad_desercion = models.DecimalField(
        max_digits=6, decimal_places=4,
        verbose_name="Probabilidad de deserción (0–1)"
    )
    factores_shap = models.JSONField(
        blank=True, null=True,
        verbose_name="Valores SHAP por factor"
    )
    fecha_prediccion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de predicción")
    recomendacion_llm = models.TextField(
        blank=True, null=True,
        verbose_name="Recomendación generada por LLM"
    )
    modelo_version = models.CharField(max_length=50, blank=True, null=True, verbose_name="Versión del modelo")

    class Meta:
        verbose_name = "Predicción"
        verbose_name_plural = "Predicciones"
        ordering = ['-fecha_prediccion']
        unique_together = ('alumno', 'periodo')

    def __str__(self):
        return f"{self.alumno} — {self.periodo}: {self.nivel_riesgo} ({self.probabilidad_desercion:.2%})"

    @property
    def probabilidad_porcentaje(self):
        return float(self.probabilidad_desercion or 0) * 100

    @property
    def color_semaforo(self):
        colores = {'ALTO': 'danger', 'MEDIO': 'warning', 'BAJO': 'success'}
        return colores.get(self.nivel_riesgo, 'secondary')

    @property
    def emoji_semaforo(self):
        emojis = {'ALTO': '🔴', 'MEDIO': '🟡', 'BAJO': '🟢'}
        return emojis.get(self.nivel_riesgo, '⚪')

    @property
    def principales_factores(self):
        """Retorna los 3 factores SHAP más influyentes."""
        if not self.factores_shap:
            return []
        sorted_factors = sorted(
            self.factores_shap.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        return sorted_factors[:3]


class ArchivosCargados(TimeStampedModel):
    TIPOS = [
        ('calificaciones', 'Calificaciones'),
        ('asistencias', 'Asistencias'),
        ('encuesta', 'Encuesta socioeconómica'),
        ('mixto', 'Datos mixtos'),
    ]
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('procesado', 'Procesado'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre_archivo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to='uploads/', blank=True, null=True)
    tipo = models.CharField(max_length=30, choices=TIPOS)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    registros_procesados = models.IntegerField(default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    error_mensaje = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Archivo cargado"
        verbose_name_plural = "Archivos cargados"
        ordering = ['-fecha_carga']

    def __str__(self):
        return f"{self.nombre_archivo} ({self.estado})"
