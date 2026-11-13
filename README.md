# AI Support Engine

Prototipo de clasificación de solicitudes de soporte con dos motores bajo un mismo contrato: reglas deterministas y generación real mediante el proxy local de Hermes Agent.

## Equipo

Proyecto: **AI Support Engine** · Materias: **PWA y DMI**.

- Carlos Olaya Gutiérrez
- Alexis Montalvo Osorio
- Carlos Alberto Pacheco Avila

## Colaboración

Las reglas completas están en [AGENTS.md](AGENTS.md). Cada tarea usa su propia rama y se entrega mediante Pull Request hacia `main`. No se permite push directo a `main`, force push ni fusionar sin autorización explícita de Charly. Codex y Hermes trabajan en ramas separadas y nunca se suben secretos.

## Requisitos

- Windows 10/11, Python 3.12 o posterior y `uv`.
- Hermes Agent instalado y autenticado con un proveedor compatible. Este proyecto usa Nous Portal mediante `hermes proxy`; el modelo predeterminado es `nous/welcome`.

La integración usa el proxy local de Hermes en `127.0.0.1:8645`. No guarda claves del proveedor en el repositorio. Las solicitudes enviadas al modo `generative` salen del equipo hacia el proveedor configurado en Hermes; utiliza datos sintéticos para las pruebas y no envíes información personal o confidencial sin autorización.

## Instalación y ejecución

En la carpeta del proyecto:

```powershell
uv sync --all-groups
uv run pytest -q
```

Abre una terminal para el proxy de Hermes y déjala abierta:

```powershell
hermes proxy start --provider nous --host 127.0.0.1 --port 8645
```

En otra terminal, inicia la API:

```powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

La API solo escucha en localhost. Comprueba `http://127.0.0.1:8000/health`.

### Ejemplo de petición

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/analyze `
  -H "Content-Type: application/json" `
  -d '{"message":"No puedo iniciar sesión","mode":"generative"}'
```

Cambia `mode` a `traditional` para usar únicamente reglas. La respuesta contiene `category`, `priority`, `response`, `requiresHumanReview` y `mode`. Los modos aceptados son `traditional` y `generative`.

### Configuración opcional

- `HERMES_PROXY_URL`: URL base del proxy; valor predeterminado `http://127.0.0.1:8645/v1`. HTTP solo se permite para localhost; las URL remotas requieren HTTPS.
- `HERMES_MODEL`: modelo expuesto por el proxy; valor predeterminado `nous/welcome`.
- `HERMES_TIMEOUT_SECONDS`: tiempo de espera, predeterminado `60`.
- `HERMES_PROXY_API_KEY`: token de acceso si el proxy remoto lo requiere. El proxy local de Hermes acepta un token ficticio y no necesita una clave del proveedor en este proyecto.

No se sustituye un fallo del proveedor por una respuesta inventada: el endpoint devuelve HTTP 502 si Hermes falla o si el modelo entrega JSON inválido.

## Pruebas y comparación

Con el proxy y la API activos, ejecuta:

```powershell
uv run python -m app.benchmark
```

El script envía los 12 casos de `data/benchmark_cases.json` a ambos modos a través del endpoint HTTP. Incluye solicitudes normales, ambiguas y dos intentos de inyección de instrucciones. Guarda las respuestas recibidas, validación del contrato y métricas en `reports/results.csv` y `reports/summary.json`.

Para una comprobación rápida sin invocar el modelo para todos los casos:

```powershell
uv run python -m app.benchmark --limit 2
```

Las etiquetas de referencia se definieron antes de ejecutar los motores y están junto a cada caso. El porcentaje de categoría mide coincidencia con `expected_category`; el de prioridad mide coincidencia con `expected_priority`; el exacto exige que ambos coincidan. Una señal de seguridad de alta confianza fuerza `SECURITY`, eleva la prioridad mínima según las reglas de seguridad y activa `requiresHumanReview`, incluso si el modelo intenta rebajar el incidente.

### Resultado medido

Ejecución real: 12 casos por motor, 24 peticiones al endpoint, modelo generativo `nous/welcome`.

| Motor | Formato válido | Categoría correcta | Prioridad correcta | Categoría + prioridad |
|---|---:|---:|---:|---:|
| Tradicional | 100% | 100% (12/12) | 100% (12/12) | 100% (12/12) |
| Generativo | 100% | 100% (12/12) | 83.3% (10/12) | 83.3% (10/12) |

En esta ejecución el motor generativo se equivocó en dos prioridades: `CRITICAL` en vez de `HIGH` para el bloqueo de todo el equipo y `LOW` en vez de `MEDIUM` para el caso ambiguo del reporte. Las categorías y el formato fueron correctos en los 12 casos. Los resultados completos están en `reports/results.csv`; la conclusión técnica breve está en `reports/conclusion.md`.

## Estructura

- `app/main.py`: API FastAPI y `POST /api/analyze`.
- `app/rules.py`: motor tradicional sin llamadas a modelos.
- `app/generative.py`: llamada HTTP real al proxy compatible con OpenAI de Hermes; validación estricta del JSON.
- `app/evaluation.py`, `app/benchmark.py`: comprobación del contrato, comparación y métricas.
- `data/benchmark_cases.json`: casos y etiquetas de referencia.
- `tests/`: pruebas unitarias y de API.
- `reports/`: CSV de resultados, resumen JSON y conclusión.

### Validación adicional de respuestas

El filtro de solicitudes de secretos se aplica a todas las categorías, incluido ACCESS. Rechaza con HTTP 502 las respuestas que detecta pidiendo contraseñas o tokens. Es un filtro heurístico y no garantiza detectar todas las formulaciones posibles.

`.env.example` documenta las variables disponibles; la aplicación no carga archivos `.env` automáticamente. Configura las variables en la terminal antes de iniciar la API.

## Verificación de la entrega

- Motor tradicional: `app/rules.py`, cuatro categorías y cuatro niveles de prioridad, sin modelo.
- Motor generativo: `app/generative.py`, petición real al proveedor mediante Hermes y validación del JSON.
- API y errores: `app/main.py`, `app/schemas.py`; solicitudes inválidas producen 422 y fallos del proveedor, 502.
- Seguridad: revisión humana para SECURITY, guardarraíl de prioridad y filtro heurístico de solicitudes de secretos.
- Comparación: 12 casos por motor, referencias en `data/benchmark_cases.json`, respuestas y métricas en `reports/`.
- Verificación automatizada: 45 pruebas; incluye recomputar las métricas guardadas y comprobar el límite de palabras de la conclusión.

Las pruebas unitarias simulan fallos y respuestas del proveedor para verificar el manejo de errores; no se presentan como evidencia de generación real. El CSV conserva la ejecución previa realizada con Hermes. La revisión posterior comprobó su coherencia y no repitió las llamadas al modelo. Las métricas generativas corresponden al sistema completo con guardarraíles, no al modelo aislado.

**Atención:** ejecutar el benchmark, incluso con `--limit`, sobrescribe los archivos de resultados. Conserva una copia de las evidencias antes de repetirlo.

## Interfaz gráfica

Con la API iniciada, abre http://127.0.0.1:8000/ en el navegador. Permite elegir motor, cargar ejemplos, analizar solicitudes y copiar la respuesta o consultar su JSON. El modo tradicional funciona sin Hermes; para el generativo inicia también el proxy. La interfaz no guarda mensajes en almacenamiento del navegador.

Validación de interfaz: navegador Chrome a 1440 y 390 píxeles, solicitudes tradicionales reales de acceso/falla/seguridad, recuperación ante HTTP 502 simulado y ausencia de errores JavaScript. No se repitieron llamadas generativas reales en esta validación.
