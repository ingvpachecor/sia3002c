from django.contrib import admin
from .models import Escuela, Grupo, Periodo, Alumno, Calificacion, Asistencia


@admin.register(Escuela)
class EscuelaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cct', 'municipio', 'estado')
    search_fields = ('nombre', 'cct', 'municipio')


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'escuela', 'grado', 'turno', 'ciclo_escolar', 'total_alumnos')
    list_filter = ('grado', 'turno', 'escuela')
    search_fields = ('nombre', 'escuela__nombre')


@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ciclo_escolar', 'fecha_inicio', 'fecha_fin')
    list_filter = ('ciclo_escolar',)


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'curp', 'grupo', 'genero', 'becado', 'acceso_internet', 'activo')
    list_filter = ('genero', 'becado', 'acceso_internet', 'activo', 'grupo__escuela')
    search_fields = ('nombre', 'curp')
    raw_id_fields = ('grupo',)


@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'periodo', 'materia', 'calificacion', 'reprobada')
    list_filter = ('periodo', 'materia')
    search_fields = ('alumno__nombre', 'materia')


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'periodo', 'total_clases', 'clases_asistidas', 'porcentaje_asistencia')
    list_filter = ('periodo',)
    search_fields = ('alumno__nombre',)
