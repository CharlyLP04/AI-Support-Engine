# Reglas de colaboración

## Git y GitHub
- Nunca hacer push directamente a main.
- Nunca trabajar ni hacer commits directamente en main.
- Crear una rama por tarea: feat/..., fix/..., test/... o docs/...
- Entregar los cambios mediante Pull Request hacia main.
- No fusionar Pull Requests sin autorización explícita de Charly.
- No usar force push ni reescribir historial compartido.
- No borrar ramas remotas ni archivos ajenos sin autorización.
- Antes de modificar archivos, revisar git status y respetar cambios existentes.

## Coordinación
- Codex y Hermes deben trabajar en ramas separadas.
- Acordar qué archivos modifica cada agente para evitar conflictos.
- Hacer commits pequeños con mensajes claros.
- Explicar qué cambió, cómo se verificó y qué queda pendiente.

## Seguridad
- Nunca subir credenciales, tokens, contraseñas ni archivos .env.
- Mantener .env en .gitignore y proporcionar .env.example sin secretos.
- No incluir datos personales ni secretos en logs o evidencias.

## Calidad y entrega
- Mantener el mismo contrato JSON para ambos motores.
- Validar entradas y respuestas del modelo.
- Marcar posibles incidentes de seguridad para revisión humana.
- Ejecutar las pruebas pertinentes antes de abrir un Pull Request.
- No inventar respuestas generativas, evidencias ni resultados de pruebas.
- Actualizar el README cuando cambien los pasos de ejecución.
