const $ = (id) => document.getElementById(id);
const form = $('analyze-form');
const message = $('message');
let latest = null;
const categories = { ACCESS: 'Acceso', BUG: 'Falla del sistema', FEATURE: 'Funcionalidad', SECURITY: 'Seguridad' };
const priorities = { LOW: 'Baja', MEDIUM: 'Media', HIGH: 'Alta', CRITICAL: 'Crítica' };
function updateCount() { $('count').textContent = `${message.value.length} / 4000`; message.setCustomValidity(''); }
message.addEventListener('input', updateCount);
document.querySelectorAll('[data-example]').forEach(button => button.addEventListener('click', () => { message.value = button.dataset.example; updateCount(); message.focus(); }));
form.addEventListener('change', () => { $('privacy').textContent = form.elements.mode.value === 'generative' ? 'El mensaje se enviará al proveedor de IA configurado. Usa datos sintéticos y no incluyas contraseñas ni información confidencial.' : 'El motor tradicional analiza el mensaje mediante reglas, sin enviarlo a un modelo.'; });
form.addEventListener('submit', async event => {
  event.preventDefault();
  if ($('submit').disabled) return;
  if (!message.value.trim()) { message.setCustomValidity('Escribe una solicitud, no solo espacios.'); message.reportValidity(); return; }
  const payload = { message: message.value.trim(), mode: form.elements.mode.value };
  const start = performance.now();
  latest = null;
  $('copy').textContent = 'Copiar';
  $('empty').hidden = true; $('result').hidden = true; $('error').hidden = true; $('loading').hidden = false;
  $('submit').disabled = true;
  document.querySelector('.result-panel').setAttribute('aria-busy', 'true');
  $('status').textContent = 'Analizando solicitud.';
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  try {
    const res = await fetch('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal: controller.signal });
    if (!res.ok) throw new Error(res.status === 502 ? 'El motor generativo no está disponible o devolvió una respuesta inválida. Comprueba que Hermes esté activo y vuelve a intentarlo.' : res.status === 422 ? 'Revisa el mensaje y el motor seleccionado antes de intentarlo de nuevo.' : 'No se pudo completar el análisis. Inténtalo de nuevo.');
    const data = await res.json();
    if (!Object.hasOwn(categories, data.category) || !Object.hasOwn(priorities, data.priority) || typeof data.response !== 'string' || !data.response.trim() || typeof data.requiresHumanReview !== 'boolean' || data.mode !== payload.mode || (data.category === 'SECURITY' && !data.requiresHumanReview)) throw new Error('La respuesta del servidor no tiene el formato esperado. Inténtalo de nuevo.');
    latest = data;
    $('category').textContent = categories[data.category];
    $('priority').textContent = priorities[data.priority]; $('priority').dataset.priority = data.priority;
    $('engine-label').textContent = data.mode === 'generative' ? 'Motor generativo' : 'Motor tradicional';
    $('elapsed').textContent = `${((performance.now() - start) / 1000).toFixed(1)} s`;
    $('review').textContent = data.requiresHumanReview ? '⚑ Requiere revisión humana por el equipo de seguridad' : '✓ Sin revisión humana requerida por el motor';
    $('review').classList.toggle('warning', data.requiresHumanReview);
    $('response').textContent = data.response;
    $('json').textContent = JSON.stringify(data, null, 2);
    $('result').hidden = false;
    $('status').textContent = `Análisis completo: ${categories[data.category]}, prioridad ${priorities[data.priority]}.${data.requiresHumanReview ? ' Requiere revisión humana.' : ''}`;
  } catch (error) {
    $('error').textContent = error.name === 'AbortError' ? 'El análisis tardó demasiado. Comprueba el proveedor e inténtalo de nuevo.' : error instanceof TypeError ? 'No se pudo conectar con el servidor. Comprueba que la API esté activa.' : error.message;
    $('error').hidden = false; $('empty').hidden = false;
    $('status').textContent = 'El análisis no se completó.';
  } finally {
    clearTimeout(timer); $('loading').hidden = true; $('submit').disabled = false;
    document.querySelector('.result-panel').setAttribute('aria-busy', 'false');
  }
});
$('copy').addEventListener('click', async () => {
  if (!latest) return;
  try { await navigator.clipboard.writeText(latest.response); $('copy').textContent = 'Copiado'; }
  catch { $('copy').textContent = 'Selecciona el texto para copiar'; }
});
