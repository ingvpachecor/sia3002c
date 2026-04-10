from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Alumno, Grupo


@login_required
def lista_alumnos(request):
    grupo_id = request.GET.get('grupo')
    riesgo = request.GET.get('riesgo')
    query = request.GET.get('q', '')
    
    alumnos = Alumno.objects.filter(activo=True, grupo__ciclo_escolar='2026-2027').select_related('grupo', 'grupo__escuela')
    
    if grupo_id:
        alumnos = alumnos.filter(grupo_id=grupo_id)
    if query:
        alumnos = alumnos.filter(nombre__icontains=query)
    
    grupos = Grupo.objects.filter(ciclo_escolar='2026-2027').select_related('escuela')
    
    context = {
        'alumnos': alumnos,
        'grupos': grupos,
        'grupo_id': grupo_id,
        'query': query,
        'titulo': 'Alumnos — SIA3002C',
    }
    return render(request, 'alumnos/lista.html', context)


@login_required
def detalle_alumno(request, pk):
    alumno = get_object_or_404(Alumno, pk=pk)
    calificaciones = alumno.calificaciones.all().select_related('periodo').order_by('-periodo__fecha_inicio')
    asistencias = alumno.asistencias.all().select_related('periodo').order_by('-periodo__fecha_inicio')
    predicciones = alumno.predicciones.all().select_related('periodo').order_by('-fecha_prediccion')
    
    context = {
        'alumno': alumno,
        'calificaciones': calificaciones,
        'asistencias': asistencias,
        'predicciones': predicciones,
        'titulo': f'{alumno.nombre} — SIA3002C',
    }
    return render(request, 'alumnos/detalle.html', context)


@login_required
def lista_grupos(request):
    grupos = Grupo.objects.filter(ciclo_escolar='2026-2027').select_related('escuela')
    context = {
        'grupos': grupos,
        'titulo': 'Grupos — SIA3002C',
    }
    return render(request, 'alumnos/grupos.html', context)
