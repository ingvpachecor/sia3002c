from django.contrib import admin
from .models import Prediccion, ArchivosCargados


@admin.register(Prediccion)
class PrediccionAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'periodo', 'nivel_riesgo', 'probabilidad_desercion', 'fecha_prediccion')
    list_filter = ('nivel_riesgo', 'periodo')
    search_fields = ('alumno__nombre',)
    readonly_fields = ('fecha_prediccion', 'factores_shap', 'recomendacion_llm')


@admin.register(ArchivosCargados)
class ArchivosCargadosAdmin(admin.ModelAdmin):
    list_display = ('nombre_archivo', 'tipo', 'estado', 'registros_procesados', 'fecha_carga')
    list_filter = ('tipo', 'estado')
    readonly_fields = ('fecha_carga',)
