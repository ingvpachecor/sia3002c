from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Prediccion, ArchivosCargados


@login_required
def lista_predicciones(request):
    predicciones = Prediccion.objects.filter(alumno__grupo__ciclo_escolar='2026-2027').select_related('alumno', 'periodo').order_by('-fecha_prediccion')
    context = {
        'predicciones': predicciones,
        'titulo': 'Predicciones — SIA3002C',
    }
    return render(request, 'prediccion/lista.html', context)


@login_required
def ejecutar_prediccion(request):
    """Ejecuta el modelo IA para todos los alumnos activos."""
    if request.method == 'POST':
        from .ml.predictor import ejecutar_prediccion_batch
        from alumnos.models import Periodo
        
        periodo_id = request.POST.get('periodo_id')
        try:
            periodo = Periodo.objects.get(pk=periodo_id)
            resultado = ejecutar_prediccion_batch(periodo)
            messages.success(request, f"✅ Predicción ejecutada: {resultado['procesados']} alumnos analizados.")
        except Exception as e:
            messages.error(request, f"❌ Error al ejecutar predicción: {str(e)}")
        return redirect('prediccion:lista')
    
    from alumnos.models import Periodo
    periodos = Periodo.objects.filter(ciclo_escolar='2026-2027').order_by('-fecha_inicio')
    return render(request, 'prediccion/ejecutar.html', {'periodos': periodos})


@login_required
def cargar_archivo(request):
    """Vista para subir archivos CSV/Excel con datos de alumnos."""
    if request.method == 'POST':
        archivo = request.FILES.get('archivo')
        tipo = request.POST.get('tipo', 'mixto')
        
        if not archivo:
            messages.error(request, "❌ Debes seleccionar un archivo.")
            return redirect('prediccion:cargar')
        
        registro = ArchivosCargados.objects.create(
            nombre_archivo=archivo.name,
            archivo=archivo,
            tipo=tipo,
            estado='pendiente'
        )
        
        try:
            from .ml.data_loader import procesar_archivo
            registros = procesar_archivo(registro)
            registro.registros_procesados = registros
            registro.estado = 'procesado'
            registro.save()
            messages.success(request, f"✅ Archivo procesado: {registros} registros cargados.")
        except Exception as e:
            registro.estado = 'error'
            registro.error_mensaje = str(e)
            registro.save()
            messages.error(request, f"❌ Error al procesar: {str(e)}")
        
        return redirect('prediccion:lista')
    
    archivos = ArchivosCargados.objects.all().order_by('-fecha_carga')[:10]
    return render(request, 'prediccion/cargar.html', {'archivos': archivos})


@login_required
def generar_datos_sinteticos(request):
    """Genera y carga datos sintéticos de demostración."""
    if request.method == 'POST':
        modo = request.POST.get('modo', 'actual')
        try:
            from .ml.generate_data import generar_y_cargar_datos
            resultado = generar_y_cargar_datos(modo=modo)
            messages.success(request, f"✅ Datos sintéticos ({modo}) generados: {resultado} registros.")
        except Exception as e:
            messages.error(request, f"❌ Error: {str(e)}")
        return redirect('dashboard:dashboard')
    return render(request, 'prediccion/generar_datos.html')


@login_required
def detalle_prediccion(request, pk):
    prediccion = get_object_or_404(Prediccion, pk=pk)
    
    prob_porcentaje = int(float(prediccion.probabilidad_desercion) * 100)
    
    factores_ui = []
    if prediccion.factores_shap:
        # Encontrar el mayor valor absoluto para escalar la longitud de las barras
        max_abs = max(abs(float(v)) for v in prediccion.factores_shap.values()) if prediccion.factores_shap else 1.0
        if max_abs == 0:
            max_abs = 1.0
        
        for k, v in prediccion.factores_shap.items():
            valor = float(v)
            width_pct = (abs(valor) / max_abs) * 100
            factores_ui.append({
                'nombre': k,
                'valor': valor,
                'positivo': valor > 0,
                'width_pct': width_pct
            })
            
    context = {
        'prediccion': prediccion,
        'prob_porcentaje': prob_porcentaje,
        'factores_ui': factores_ui,
        'titulo': f'Predicción — {prediccion.alumno.nombre}',
    }
    return render(request, 'prediccion/detalle.html', context)


@login_required
def generar_recomendacion(request, pk):
    """Genera recomendación LLM para una predicción existente."""
    prediccion = get_object_or_404(Prediccion, pk=pk)
    if request.method == 'POST':
        try:
            from .ml.llm_service import generar_recomendacion_gemini
            recomendacion = generar_recomendacion_gemini(prediccion)
            prediccion.recomendacion_llm = recomendacion
            prediccion.save()
            messages.success(request, "✅ Recomendación generada con éxito.")
        except Exception as e:
            messages.error(request, f"❌ Error al generar recomendación: {str(e)}")
    return redirect('prediccion:detalle', pk=pk)


@login_required
def rendimiento_modelo(request):
    """Muestra métricas y gráficas del modelo XGBoost si ya fue entrenado."""
    from django.conf import settings
    from pathlib import Path
    import json
    import base64

    models_dir = Path(settings.ML_MODELS_DIR)
    metrics_file = models_dir / 'metrics.json'
    
    context = {'titulo': 'Rendimiento del Modelo XGBoost'}
    
    if metrics_file.exists():
        with open(metrics_file, 'r') as f:
            metrics_data = json.load(f)
        context['metrics'] = metrics_data
        
        # Cargar imagenes en base64 para evitar problemas de estáticos locales temporales
        graficas = ['roc_curve.png', 'confusion_matrix.png', 'feature_importance.png']
        encoded = {}
        for fname in graficas:
            fpath = models_dir / fname
            if fpath.exists():
                with open(fpath, "rb") as image_file:
                    encoded[fname.split('.')[0]] = base64.b64encode(image_file.read()).decode('utf-8')
        context['graficas'] = encoded
    else:
        context['metrics'] = None

    return render(request, 'prediccion/rendimiento.html', context)


@login_required
def entrenar_modelo_view(request):
    """Interfaz gráfica para disparar el reentrenamiento de XGBoost."""
    if request.method == 'POST':
        try:
            from .ml.train_model import entrenar_modelo
            resultado = entrenar_modelo()
            messages.success(request, f"✅ Modelo XGBoost entrenado exitosamente con {resultado['n_train']} registros de entrenamiento. Métricas generadas.")
            return redirect('prediccion:rendimiento')
        except Exception as e:
            messages.error(request, f"❌ Error crítico al entrenar el modelo: {str(e)}")
            return redirect('prediccion:entrenar_modelo')
            
    return render(request, 'prediccion/entrenar.html', {'titulo': 'Entrenar Modelo IA'})
