"""
train_model.py — SIA3002C
Script para entrenar el modelo XGBoost de predicción de deserción escolar.
Genera datos de entrenamiento desde la base de datos y guarda el modelo en disco.

Uso:
    python prediccion/ml/train_model.py

O desde Django shell:
    from prediccion.ml.train_model import entrenar_modelo
    resultado = entrenar_modelo()
"""
import os
import pickle
import numpy as np
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sia3002c.settings')


def obtener_features_desde_db():
    """
    Extrae todas las variables del modelo desde la base de datos Django.
    Retorna: (X DataFrame, y Series)
    """
    import pandas as pd
    from alumnos.models import Alumno, Calificacion, Asistencia

    alumnos = Alumno.objects.filter(activo=True, grupo__ciclo_escolar__lt='2026-2027').select_related('grupo')
    
    rows = []
    for alumno in alumnos:
        # Calificaciones promedio y materias reprobadas (todos los periodos)
        cals = Calificacion.objects.filter(alumno=alumno)
        if not cals.exists():
            continue
        
        promedio = float(cals.aggregate(avg=__import__('django.db.models', fromlist=['Avg']).Avg('calificacion'))['avg'] or 7.0)
        periodos_evaluados = max(cals.values('periodo').distinct().count(), 1)
        materias_reprobadas = cals.filter(calificacion__lt=6).count() / periodos_evaluados
        
        # Asistencia promedio
        asists = Asistencia.objects.filter(alumno=alumno)
        if asists.exists():
            pct_list = [a.porcentaje_asistencia for a in asists]
            pct_asistencia = sum(pct_list) / len(pct_list)
        else:
            pct_asistencia = 85.0
        
        # Mapear nivel de estudios a número
        nivel_map = {'Sin': 0, 'Primaria': 1, 'Secundaria': 2, 'Bachillerato': 3, 'Superior': 4}
        nivel_padre = nivel_map.get(alumno.nivel_estudios_padre or 'Secundaria', 2)
        nivel_madre = nivel_map.get(alumno.nivel_estudios_madre or 'Secundaria', 2)
        
        # Predicción más reciente como etiqueta
        ultima_pred = alumno.predicciones.order_by('-fecha_prediccion').first()
        if ultima_pred:
            y = 1 if ultima_pred.nivel_riesgo == 'ALTO' else 0
        else:
            y = 0
        
        rows.append({
            'promedio': promedio,
            'materias_reprobadas': materias_reprobadas,
            'pct_asistencia': float(pct_asistencia),
            'ingreso_familiar': float(alumno.ingreso_familiar or 8000),
            'becado': int(alumno.becado),
            'distancia_escuela_km': float(alumno.distancia_escuela_km or 5.0),
            'nivel_estudios_padre': nivel_padre,
            'nivel_estudios_madre': nivel_madre,
            'acceso_internet': int(alumno.acceso_internet),
            'label': y
        })
    
    import pandas as pd
    df = pd.DataFrame(rows)
    X = df.drop('label', axis=1)
    y = df['label']
    return X, y


def entrenar_modelo():
    """
    Entrena el modelo XGBoost con los datos de la base de datos (Histórico).
    Aplica SMOTE para balanceo de clases.
    Guarda el modelo entrenado en disco.
    
    Returns: dict con métricas del modelo
    """
    django.setup()
    
    from django.conf import settings
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix, roc_curve
    from imblearn.over_sampling import SMOTE
    from xgboost import XGBClassifier
    import pandas as pd
    import json
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    seed = getattr(settings, 'RANDOM_SEED', 42)
    
    print("📊 Extrayendo datos de historial (<= 2025-2026) desde la base de datos...")
    X, y = obtener_features_desde_db()
    
    if len(X) < 50:
        raise ValueError(f"Datos insuficientes: {len(X)} muestras historicas. Genera datos sintéticos HISTÓRICOS primero.")
    
    print(f"   Total de muestras históricas: {len(X)} alumnos")
    print(f"   Distribución de clases: Riesgo Alto={y.sum()} ({y.mean():.1%}), Bajo={(~y.astype(bool)).sum()}")

    # ── Split ───────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )
    
    # ── SMOTE para balanceo ──────────────────────────
    print("⚖️  Aplicando SMOTE para balanceo de clases...")
    smote = SMOTE(random_state=seed)
    X_train_bal, y_train_bal = smote.fit_resample(X_train, y_train)
    print(f"   Después de SMOTE: {len(X_train_bal)} muestras balanceadas")
    
    # ── Escalado ─────────────────────────────────────
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_bal)
    X_test_scaled = scaler.transform(X_test)
    
    # ── Modelo XGBoost ───────────────────────────────
    print("🤖 Entrenando modelo XGBoost...")
    modelo = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric='logloss',
        random_state=seed,
        n_jobs=-1
    )
    modelo.fit(X_train_scaled, y_train_bal)
    
    # ── Evaluación ───────────────────────────────────
    y_pred = modelo.predict(X_test_scaled)
    y_prob = modelo.predict_proba(X_test_scaled)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    report = classification_report(y_test, y_pred, output_dict=True)
    
    print(f"\n📈 Resultados del modelo:")
    print(f"   AUC-ROC: {auc:.4f}")
    print(f"   Accuracy: {report['accuracy']:.4f}")
    print(f"   Recall (Sensibilidad - Riesgo Alto): {report.get('1', {}).get('recall', 0):.4f}")
    print(f"   F1 (Riesgo Alto): {report.get('1', {}).get('f1-score', 0):.4f}")
    
    # ── Guardar modelo y scaler ──────────────────────
    models_dir = Path(settings.ML_MODELS_DIR)
    models_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = models_dir / 'modelo_xgboost.pkl'
    scaler_path = models_dir / 'scaler.pkl'
    features_path = models_dir / 'features.pkl'
    
    with open(model_path, 'wb') as f:
        pickle.dump(modelo, f)
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    with open(features_path, 'wb') as f:
        pickle.dump(list(X.columns), f)
    
    # ── Generar y guardar gráficas (Rendimiento) ──────
    print("🎨 Generando gráficas de rendimiento...")
    
    # 1. Matriz de confusión
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Bajo/Medio', 'Alto'], yticklabels=['Bajo/Medio', 'Alto'])
    plt.title('Matriz de Confusión')
    plt.ylabel('Real')
    plt.xlabel('Predicho')
    plt.tight_layout()
    plt.savefig(models_dir / 'confusion_matrix.png', dpi=100)
    plt.close()
    
    # 2. Curva ROC
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {auc:.4f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('Tasa de Falsos Positivos')
    plt.ylabel('Tasa de Verdaderos Positivos')
    plt.title('Curva ROC')
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(models_dir / 'roc_curve.png', dpi=100)
    plt.close()
    
    # 3. Importancia de Variables
    importances = modelo.feature_importances_
    features_list = list(X.columns)
    
    # Pair and sort
    feat_impl = sorted(zip(features_list, importances), key=lambda x: x[1], reverse=False)
    sorted_features = [x[0] for x in feat_impl]
    sorted_importances = [x[1] for x in feat_impl]
    
    plt.figure(figsize=(7, 5))
    plt.barh(range(len(sorted_features)), sorted_importances, color='teal')
    plt.yticks(range(len(sorted_features)), sorted_features)
    plt.xlabel('Importancia Relativa')
    plt.title('Importancia de Variables (XGBoost)')
    plt.tight_layout()
    plt.savefig(models_dir / 'feature_importance.png', dpi=100)
    plt.close()
    
    print("✅ Gráficas guardadas en el directorio de modelos.")
    
    # ── Guardar metrics.json ─────────────────────────
    metrics_data = {
        'auc': round(auc, 4),
        'accuracy': round(report['accuracy'], 4),
        'recall_alto': round(report.get('1', {}).get('recall', 0), 4),
        'f1_alto': round(report.get('1', {}).get('f1-score', 0), 4),
        'n_train': len(X_train_bal),
        'n_test': len(X_test),
        'model_path': str(model_path),
        'report_json': report,
        'cm': cm.tolist()
    }
    with open(models_dir / 'metrics.json', 'w') as f:
        json.dump(metrics_data, f, indent=4)
    
    print(f"\n✅ Modelo y métricas guardados en: {models_dir}")
    
    return metrics_data


if __name__ == '__main__':
    resultado = entrenar_modelo()
    print(f"\nResumen: {resultado}")
