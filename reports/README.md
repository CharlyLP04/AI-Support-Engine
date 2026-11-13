# Evidencias de comparación

Esta carpeta conserva los artefactos de una ejecución del benchmark con los
casos definidos en `data/benchmark_cases.json`.

- `results.csv`: una fila por caso y motor, con la respuesta recibida y la
  evaluación frente a la etiqueta de referencia.
- `summary.json`: métricas agregadas, modelo generativo informado y fecha de
  generación en UTC.
- `conclusion.md`: interpretación breve de los resultados guardados.

Los resultados son evidencia de la ejecución registrada; no deben presentarse
como una garantía de rendimiento para entradas distintas. Para regenerarlos se
necesitan el proxy de Hermes y la API en ejecución, y se usa:

```powershell
uv run python -m app.benchmark
```

El benchmark sobrescribe `results.csv` y `summary.json`. Conserva una copia de
los artefactos antes de ejecutarlo de nuevo.
