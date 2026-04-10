"""
Modelos de la app 'alumnos' — SIA3002C
Incluye: Escuela, Grupo, Periodo, Alumno, Calificacion, Asistencia
"""
import uuid
from django.db import models


class TimeStampedModel(models.Model):
    """Mixin base con timestamps automáticos."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Escuela(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la escuela")
    cct = models.CharField(max_length=15, blank=True, null=True, verbose_name="Clave CCT")
    municipio = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Escuela"
        verbose_name_plural = "Escuelas"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Grupo(TimeStampedModel):
    GRADOS = [(1, '1° Semestre'), (2, '2° Semestre'), (3, '3° Semestre')]
    TURNOS = [('Matutino', 'Matutino'), ('Vespertino', 'Vespertino'), ('Nocturno', 'Nocturno')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escuela = models.ForeignKey(Escuela, on_delete=models.CASCADE, related_name='grupos')
    nombre = models.CharField(max_length=100, verbose_name="Nombre del grupo")
    grado = models.SmallIntegerField(choices=GRADOS)
    turno = models.CharField(max_length=20, choices=TURNOS)
    ciclo_escolar = models.CharField(max_length=20, blank=True, null=True, verbose_name="Ciclo escolar")

    class Meta:
        verbose_name = "Grupo"
        verbose_name_plural = "Grupos"
        ordering = ['escuela', 'grado', 'nombre']

    def __str__(self):
        return f"{self.nombre} — {self.escuela.nombre}"

    @property
    def total_alumnos(self):
        return self.alumnos.filter(activo=True).count()


class Periodo(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, verbose_name="Nombre del periodo")
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de fin")
    ciclo_escolar = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = "Periodo"
        verbose_name_plural = "Periodos"
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.nombre} ({self.ciclo_escolar or ''})"


class Alumno(TimeStampedModel):
    GENEROS = [('M', 'Masculino'), ('F', 'Femenino'), ('Otro', 'Otro')]
    NIVEL_ESTUDIOS = [
        ('Sin', 'Sin estudios'), ('Primaria', 'Primaria'), ('Secundaria', 'Secundaria'),
        ('Bachillerato', 'Bachillerato'), ('Superior', 'Superior')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grupo = models.ForeignKey(Grupo, on_delete=models.SET_NULL, null=True, related_name='alumnos')
    nombre = models.CharField(max_length=200, verbose_name="Nombre completo")
    curp = models.CharField(max_length=18, unique=True, blank=True, null=True, verbose_name="CURP")
    fecha_nacimiento = models.DateField(blank=True, null=True)
    genero = models.CharField(max_length=10, choices=GENEROS, blank=True, null=True)
    # Variables socioeconómicas
    ingreso_familiar = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        verbose_name="Ingreso familiar mensual (MXN)"
    )
    becado = models.BooleanField(default=False, verbose_name="¿Tiene beca?")
    distancia_escuela_km = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True,
        verbose_name="Distancia a la escuela (km)"
    )
    nivel_estudios_padre = models.CharField(
        max_length=20, choices=NIVEL_ESTUDIOS, blank=True, null=True,
        verbose_name="Nivel de estudios del padre"
    )
    nivel_estudios_madre = models.CharField(
        max_length=20, choices=NIVEL_ESTUDIOS, blank=True, null=True,
        verbose_name="Nivel de estudios de la madre"
    )
    acceso_internet = models.BooleanField(default=True, verbose_name="¿Tiene acceso a internet en casa?")
    activo = models.BooleanField(default=True, verbose_name="¿Está activo?")

    class Meta:
        verbose_name = "Alumno"
        verbose_name_plural = "Alumnos"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def ultima_prediccion(self):
        return self.predicciones.order_by('-created_at').first()


class Calificacion(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='calificaciones')
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name='calificaciones')
    materia = models.CharField(max_length=100, verbose_name="Materia")
    calificacion = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        verbose_name = "Calificación"
        verbose_name_plural = "Calificaciones"
        unique_together = ('alumno', 'periodo', 'materia')

    def __str__(self):
        return f"{self.alumno} — {self.materia}: {self.calificacion}"

    @property
    def reprobada(self):
        return self.calificacion is not None and self.calificacion < 6


class Asistencia(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='asistencias')
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name='asistencias')
    total_clases = models.PositiveIntegerField(verbose_name="Total de clases en el periodo")
    clases_asistidas = models.PositiveIntegerField(verbose_name="Clases a las que asistió")

    class Meta:
        verbose_name = "Asistencia"
        verbose_name_plural = "Asistencias"
        unique_together = ('alumno', 'periodo')

    def __str__(self):
        return f"{self.alumno} — {self.periodo}: {self.porcentaje_asistencia:.1f}%"

    @property
    def porcentaje_asistencia(self):
        if self.total_clases > 0:
            return round((self.clases_asistidas / self.total_clases) * 100, 2)
        return 0.0
