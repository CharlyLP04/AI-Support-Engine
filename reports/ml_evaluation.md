# Evaluación de Machine Learning — AI Support Engine V2

## 1. Evaluación del modelo en conjunto `test` aislado

- **Dataset:** `data/tickets.csv` (200 registros únicos: 160 `train` / 40 `test`, sin duplicados ni fuga de datos).
- **Pipeline:** `TfidfVectorizer(ngram_range=(1, 2))` + `LogisticRegression(max_iter=1000, random_state=42)`.
- **Accuracy global en `test`:** **92.5%**
- **Recall en `SECURITY`:** **100.0%** (Falsos negativos de seguridad: 0, Falsos positivos: 1).
- **Umbral de confianza para revisión humana:** `0.45` (si `predict_proba.max() < 0.45`, se activa `requiresHumanReview: true`).

### Matriz de confusión (`test` = 40 tickets)

| Real \ Predicción | ACCESS | BUG | FEATURE | SECURITY |
|---|---:|---:|---:|---:|
| **ACCESS** | 9 | 1 | 0 | 0 |
| **BUG** | 0 | 9 | 0 | 1 |
| **FEATURE** | 1 | 0 | 9 | 0 |
| **SECURITY** | 0 | 0 | 0 | 10 |

### Reporte por clase

```text
precision    recall  f1-score   support

      ACCESS       0.90      0.90      0.90        10
         BUG       0.90      0.90      0.90        10
     FEATURE       1.00      0.90      0.95        10
    SECURITY       0.91      1.00      0.95        10

    accuracy                           0.93        40
   macro avg       0.93      0.93      0.92        40
weighted avg       0.93      0.93      0.92        40
```

## 2. Comparativa de los 3 motores (`data/benchmark_cases.json` — 12 casos)

| Motor | Accuracy categoría | Recall en SECURITY | Latencia p95 | Costo / 100 consultas | Revisión humana |
|---|---:|---:|---:|---|---:|
| Tradicional (Reglas) | 100.0% | 100.0% | 0.04 ms | $0.00 (local) | 25.0% |
| Machine Learning (TF-IDF) | 100.0% | 100.0% | 1.04 ms | $0.00 (local) | 91.7% |
| Generativo (LLM) | 100.0% | 100.0% | N/A (API externa) | Cuota API / Variable | 25.0% |

## 3. Análisis de decisiones: ¿cuándo elegir cada motor?

- **Tradicional (Reglas):** Ideal para reglas invariables, guardarraíles de seguridad y prioridades estrictas con costo cero y latencia sub-milisegundo.
- **Machine Learning (TF-IDF + LogisticRegression):** Ideal para clasificar tickets con redacción variada o sinónimos sin escribir regex por cada frase, manteniéndose local, gratuito y reproducible; respaldado por umbral de confianza y reglas de seguridad para evitar falsos negativos críticos.
- **Generativo (LLM):** Ideal cuando se requiere comprender contexto ambiguo y redactar respuestas empáticas personalizadas, asumiendo mayor latencia y necesidad de validaciones estrictas de formato y seguridad.
