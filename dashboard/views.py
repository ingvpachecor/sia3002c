from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


def index(request):
    """Redirige al dashboard si está autenticado, si no al login."""
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    return redirect('login')


@login_required
def dashboard(request):
    """Vista principal del dashboard con semáforo de riesgo."""
    from alumnos.models import Grupo, Alumno
    from prediccion.models import Prediccion
    
    grupos = Grupo.objects.filter(ciclo_escolar='2026-2027').select_related('escuela')
    total_alumnos = Alumno.objects.filter(activo=True, grupo__ciclo_escolar='2026-2027').count()
    
    # Estadísticas cruzadas: extraer solo la última predicción de cada alumno activo
    from django.db.models import Subquery, OuterRef
    
    ultimas_predicciones = Prediccion.objects.filter(
        alumno=OuterRef('pk')
    ).order_by('-created_at')

    alumnos_activos = Alumno.objects.filter(activo=True, grupo__ciclo_escolar='2026-2027').annotate(
        ultimo_riesgo=Subquery(ultimas_predicciones.values('nivel_riesgo')[:1])
    )
    
    total_alto = alumnos_activos.filter(ultimo_riesgo='ALTO').count()
    total_medio = alumnos_activos.filter(ultimo_riesgo='MEDIO').count()
    total_bajo = alumnos_activos.filter(ultimo_riesgo='BAJO').count()
    
    context = {
        'grupos': grupos,
        'total_alumnos': total_alumnos,
        'total_alto': total_alto,
        'total_medio': total_medio,
        'total_bajo': total_bajo,
        'titulo': 'Dashboard — SIA3002C',
    }
    return render(request, 'dashboard/dashboard.html', context)
