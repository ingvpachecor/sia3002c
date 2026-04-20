# SIA3002C: Sistema de Predicción de Deserción Escolar en Educación Media Superior a través de IA 🎓🧠

![Version](https://img.shields.io/badge/Versión-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.13-success)
![Django](https://img.shields.io/badge/Django-6.0.3-success)
![XGBoost](https://img.shields.io/badge/IA-XGBoost-orange)

El proyecto **SIA3002C** es un sistema web impulsado por Inteligencia Artificial diseñado como propuesta para la maestría en Inteligencia Artificial y su implementación en el ámbito de la educación media superior. Su propósito principal es detectar y prevenir la deserción escolar de manera proactiva utilizando Modelos Predictivos y Analítica de Datos Explicable.

## 🚀 Características Principales

*   **Dashboards de Monitoreo:** Semáforo logístico para visualizar rápidamente el estatus del alumnado (Riesgo Alto, Medio, Bajo).
*   **Predicción Avanzada:** Modelo de *Machine Learning* desarrollado en `XGBoost`. Entrenado utilizando hiper-parámetros regulados y técnicas de sobremuestreo (`SMOTE`) para abatir la escasez de datos.
*   **Inteligencia Artificial Explicable (XAI):** Módulo equipado con valores `SHAP` y gráficas tipo violín, posibilitando que los docentes entiendan exactamente *por qué* la IA clasificó a un estudiante como riesgo.
*   **Integración de GenAI (Gemini):** Sistema perimetral conectado a la API de *Google Gemini* para redactar diagnósticos formativos y recomendaciones tácticas estandarizadas a los docentes sobre cómo salvar al alumno.

## 💻 Arquitectura y Stack Tecnológico

El sistema se diseñó estructurado en un patrón modular web:
*   **Backend:** Python 3.13 + Django 6.0.3
*   **Motor de Inteligencia Artificial:** `xgboost`, `scikit-learn`, `imbalanced-learn`.
*   **Inteligencia Artificial Generativa:** Interoperabilidad mediante API REST con Google Gemini
*   **Intérprete Web (Frontend Vanilla):** HTML5, CSS3 Nativo estético, Chart.js.
*   **Seguridad:** Encriptamiento PBKDF2-SHA256, Middleware protector CSRF, Sesiones estrictas `@login_required` y gestión de secretos con `python-decouple`.

---

## 🛠️ Instalación y Entorno Local

Si deseas correr este proyecto en tu propia máquina (Entorno de Desarrollo):

### 1. Clonar el Repositorio
```bash
git clone https://github.com/ingvpachecor/sia3002c.git
cd sia3002c
```

### 2. Entorno Virtual y Dependencias
Se recomienda encarecidamente utilizar Python 3.13+.
```bash
# Crear entorno virtual
python -m venv pyenv_sia

# Activar en Windows
.\pyenv_sia\Scripts\activate

# Activar en Linux/Mac
source pyenv_sia/bin/activate

# Instalar los requerimientos
pip install django xgboost scikit-learn pandas shap imbalanced-learn google-genai python-decouple matplotlib
```

### 3. Variables de Entorno (.env)
Este proyecto está protegido mediante envolturas de seguridad. En la raíz del proyecto (a la altura de `manage.py`), debes crear un archivo literalmente llamado `.env` e incrustar la configuración secreta:

```ini
DEBUG=True
SECRET_KEY=coloca_aqui_una_llave_super_secreta_django
GEMINI_API_KEY=tu_api_key_de_google_gemini
ALLOWED_HOSTS=127.0.0.1, localhost
```

### 4. Base de Datos e Inicialización
```bash
python manage.py makemigrations
python manage.py migrate

# Opcional pero recomendado para crear al superusuario dashboard
python manage.py createsuperuser
```

### 5. Lanzar el Servidor
```bash
python manage.py runserver
```
Accede a `http://127.0.0.1:8000/` desde tu navegador web.

---

## 🧪 Despliegue en Producción (Cloud)
El sistema ha sido probado y se encuentra listo para inyectarse en PAAS como `PythonAnywhere`.
Para despliegue, recuerda desactivar la bandera `DEBUG=False` desde tu archivo `.env` en la nube y configurar adecuadamente la URL destino en tus `ALLOWED_HOSTS`.

## 📜 Licencia / Derechos 
Proyecto final y repositorio del Equipo 3002C (Abril 2026) enfocado para investigación como parte del Seminario de Innovación en IA de la Maestría en Inteligencia Artificial en la Universidad Internacional de la Rioja (UNIR).
