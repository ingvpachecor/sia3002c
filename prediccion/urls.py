from django.urls import path
from . import views

app_name = 'prediccion'

urlpatterns = [
    path('', views.lista_predicciones, name='lista'),
    path('ejecutar/', views.ejecutar_prediccion, name='ejecutar'),
    path('cargar/', views.cargar_archivo, name='cargar'),
    path('generar-datos/', views.generar_datos_sinteticos, name='generar_datos'),
    path('detalle/<uuid:pk>/', views.detalle_prediccion, name='detalle'),
    path('recomendacion/<uuid:pk>/', views.generar_recomendacion, name='recomendacion'),
    path('entrenar-modelo/', views.entrenar_modelo_view, name='entrenar_modelo'),
    path('rendimiento/', views.rendimiento_modelo, name='rendimiento'),
]
