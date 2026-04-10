from django.urls import path
from . import views

app_name = 'alumnos'

urlpatterns = [
    path('', views.lista_alumnos, name='lista'),
    path('<uuid:pk>/', views.detalle_alumno, name='detalle'),
    path('grupos/', views.lista_grupos, name='grupos'),
]
