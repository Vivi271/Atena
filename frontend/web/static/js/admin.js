/* ═══════════════════════════════════════════════════════════════════
 admin.js — Panel de Administración de Atena
 Gestión de documentos, preguntas, estadísticas y sistema.
 ═══════════════════════════════════════════════════════════════════ */

var API_BASE = window.API_BASE || '';
window.API_BASE = API_BASE;
let adminPin = '';
let chartVolumen = null;
let chartNiveles = null;

// ── Dark mode (compartido con app.js) ────────────────────────────────
function initTheme() {
 const saved = localStorage.getItem('atena_theme') || 'dark';
 document.documentElement.setAttribute('data-theme', saved);
}
if (typeof window.toggleTheme !== 'function') {
 window.toggleTheme = function () {
 const cur = document.documentElement.getAttribute('data-theme');
 const next = cur === 'dark' ? 'light' : 'dark';
 document.documentElement.setAttribute('data-theme', next);
 localStorage.setItem('atena_theme', next);
 };
}

// ── Login ────────────────────────────────────────────────────────────
async function loginAdmin() {
 const pinVal = document.getElementById('pin-input').value.trim();
 const errDiv = document.getElementById('login-error');
 const btn = document.getElementById('login-btn');

 if (!pinVal) return;

 btn.disabled = true;
 btn.innerHTML = '<span class="spinner"></span> Verificando…';
 errDiv.style.display = 'none';

 // Verificamos el PIN haciendo una llamada real a un endpoint protegido
 try {
 const r = await fetch(`${API_BASE}/api/admin/documents`, {
 headers: { 'X-Admin-Pin': pinVal }
 });
 if (r.status === 403) throw new Error('PIN incorrecto');
 if (!r.ok && r.status !== 200) throw new Error(`Error ${r.status}`);

 // PIN válido
 adminPin = pinVal;
 sessionStorage.setItem('atena_admin_pin', pinVal);
 localStorage.setItem('adminPin', pinVal);
 document.getElementById('login-screen').style.display = 'none';
 document.getElementById('admin-panel').style.display = 'flex';
 cargarDocs();
 } catch (e) {
 errDiv.textContent = e.message === 'PIN incorrecto' ? 'PIN incorrecto.' : `Error: ${e.message}`;
 errDiv.style.display = 'flex';
 } finally {
 btn.disabled = false;
 btn.textContent = 'Acceder';
 }
}

function logout() {
 adminPin = '';
 sessionStorage.removeItem('atena_admin_pin');
 // Redirigir a la página principal
 window.location.href = '/';
}

// ── Navegación por secciones ─────────────────────────────────────────
function showSection(id, btn) {
 document.querySelectorAll('.admin-section').forEach(s => s.style.display = 'none');
 document.querySelectorAll('.sidebar-item').forEach(b => b.classList.remove('active'));
 document.getElementById(`section-${id}`).style.display = 'block';
 if (btn) btn.classList.add('active');

 const titles = { docs: 'Documentos', preguntas: 'Banco de Preguntas', stats: 'Estadísticas', sistema: 'Sistema' };
 document.getElementById('section-title').textContent = titles[id] || '';

 if (id === 'docs') cargarDocs();
 if (id === 'preguntas') cargarPreguntas();
 if (id === 'stats') cargarStats();
 if (id === 'sistema') cargarSistema();
}

// ── Utilidades ───────────────────────────────────────────────────────
function escHtml(s) {
 return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── DOCUMENTOS ───────────────────────────────────────────────────────
async function cargarDocs() {
 const lista = document.getElementById('docs-lista');
 lista.innerHTML = '<div style="color:var(--text-muted);padding:20px;text-align:center;"><div class="spinner" style="border-top-color:var(--accent);margin:0 auto 12px;width:24px;height:24px;border-width:3px;"></div> Cargando documentos…</div>';

 try {
 const r = await fetch(`${API_BASE}/api/admin/documents`, { headers: { 'X-Admin-Pin': adminPin } });
 if (!r.ok) throw new Error(`HTTP ${r.status}`);
 const data = await r.json();
 const docs = data.documentos || [];

 if (docs.length === 0) {
 lista.innerHTML = '<div class="alert alert-info">No hay documentos indexados aún. Sube el primero usando la zona de arriba.</div>';
 return;
 }

 lista.innerHTML = `
 <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:12px;">${docs.length} documento${docs.length > 1 ? 's' : ''} indexado${docs.length > 1 ? 's' : ''}</p>
 ${docs.map(d => {
 const ext = (d.nombre.split('.').pop() || 'DOC').toUpperCase();
 const nombre = d.nombre.replace(/_/g, ' ').replace(/\.(pdf|docx)$/i, '');
 return `
 <div class="card card-accent" style="display:flex;align-items:center;gap:14px;padding:13px 18px;margin-bottom:8px;">
 <span class="badge badge-accent">${ext}</span>
 <div style="flex:1;overflow:hidden;">
 <div style="font-weight:600;font-size:0.92rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-main);">${escHtml(nombre)}</div>
 <div style="font-size:0.74rem;color:var(--text-muted);margin-top:2px;">Indexado en base vectorial RAG</div>
 </div>
 <button class="btn btn-outline" style="font-size:0.78rem;padding:5px 12px;color:#ef4444;border-color:rgba(239,68,68,0.3);"
 onclick="confirmarEliminar('${escHtml(d.nombre)}', this)">
 Eliminar
 </button>
 </div>
 `;
 }).join('')}
 `;
 } catch (e) {
 lista.innerHTML = `<div class="alert alert-error">No se pudo cargar la lista: ${escHtml(e.message)}</div>`;
 }
}

function confirmarEliminar(nombre, btn) {
 if (!confirm(`¿Eliminar "${nombre.replace(/_/g, ' ')}"?\nEsta acción no se puede deshacer.`)) return;
 eliminarDoc(nombre, btn);
}

async function eliminarDoc(nombre, btn) {
 btn.disabled = true;
 btn.textContent = '…';
 try {
 const r = await fetch(`${API_BASE}/api/admin/delete/${encodeURIComponent(nombre)}`, {
 method: 'DELETE',
 headers: { 'X-Admin-Pin': adminPin },
 });
 if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
 cargarDocs();
 } catch (e) {
 alert(`Error al eliminar: ${e.message}`);
 btn.disabled = false;
 btn.textContent = 'Eliminar';
 }
}

// ── Cambios pendientes de publicar ─────────────────────────────────────
// El botón "Publicar" inicia deshabilitado y solo se activa tras subir/reindexar
function marcarCambiosPendientes(hay) {
  const btn = document.getElementById('btn-publicar');
  const msg = document.getElementById('publicar-msg');
  if (!btn) return;
  if (hay) {
    btn.disabled = false;
    btn.title = 'Hay documentos nuevos sin publicar.';
    msg.textContent = 'Cambios pendientes. Pulsa "Publicar en la nube" para guardarlos permanentemente en GitHub.';
    msg.style.cssText = 'display:block;padding:10px 14px;border-radius:8px;font-size:0.85rem;background:rgba(251,191,36,0.1);color:#b45309;border:1px solid rgba(251,191,36,0.4);margin-bottom:14px;';
  } else {
    btn.disabled = true;
    btn.title = 'No hay cambios pendientes de publicar.';
    msg.style.display = 'none';
  }
}

async function reindexar() {
  if (!confirm('¿Reconstruir todo el índice vectorial?\nPuede tomar varios minutos.')) return;
  const btn = document.getElementById('btn-rebuild');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Indexando…';
  try {
    const r = await fetch(`${API_BASE}/api/admin/rebuild`, {
      method: 'POST',
      headers: { 'X-Admin-Pin': adminPin },
    });
    const data = await r.json();
    if (r.ok) {
      alert(`Reindexado. ${data.total_vectores ?? '?'} vectores generados.`);
      marcarCambiosPendientes(true);
    } else {
      alert(`Error: ${data.detail || r.status}`);
    }
  } catch (e) {
    alert(`Error: ${e.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Reindexar todo';
  }
}


async function publicarEnNube() {
  const btn = document.getElementById('btn-publicar');
  const msg = document.getElementById('publicar-msg');

  function setMsg(text, ok) {
    msg.style.display = 'block';
    msg.textContent   = text;
    msg.style.background = ok ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)';
    msg.style.color      = ok ? '#22c55e' : '#ef4444';
    msg.style.border     = '1px solid ' + (ok ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)');
  }

  // Paso 1: consultar la lista actual de documentos en el servidor
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Verificando…';

  let docsEnServidor = [];
  try {
    const r = await fetch(`${API_BASE}/api/admin/documents`, {
      headers: { 'X-Admin-Pin': adminPin },
    });
    if (r.ok) {
      const data = await r.json();
      docsEnServidor = (data.documentos || data.documents || []).map(d =>
        typeof d === 'string' ? d : (d.nombre || d.name || String(d))
      );
    }
  } catch(_) {}

  btn.disabled = false;
  btn.textContent = 'Publicar en la nube';

  if (docsEnServidor.length === 0) {
    setMsg('No se encontraron documentos para publicar.', false);
    return;
  }

  // Paso 2: confirmar mostrando la lista exacta de lo que se enviará a GitHub
  const lista = docsEnServidor.map(n => '  • ' + n).join('\n');
  const ok = confirm(
    'Los siguientes documentos se publicarán PERMANENTEMENTE en GitHub:\n\n' +
    lista +
    '\n\nSi alguno está equivocado, cancela y elimínalo primero desde la lista.\n\n¿Confirmar publicación?'
  );
  if (!ok) {
    setMsg('Publicación cancelada. Elimina los documentos incorrectos y vuelve a intentarlo.', false);
    return;
  }

  // Paso 3: publicar
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Publicando…';
  try {
    const r = await fetch(`${API_BASE}/api/admin/publicar`, {
      method: 'POST',
      headers: { 'X-Admin-Pin': adminPin },
    });
    const data = await r.json();
    if (r.ok) {
      setMsg(data.mensaje, true);
      marcarCambiosPendientes(false);
    } else {
      setMsg(data.detail || 'Error al publicar.', false);
      btn.disabled = false;
    }
  } catch(e) {
    setMsg('Error de red: ' + e.message, false);
    btn.disabled = false;
  } finally {
    btn.textContent = 'Publicar en la nube';
  }
}

// Drag & Drop + upload
function handleDrop(e) {
 e.preventDefault();
 document.getElementById('dropzone').classList.remove('dragover');
 subirArchivos(e.dataTransfer.files);
}

async function subirArchivos(files) {
 if (!files || files.length === 0) return;
 const prog = document.getElementById('upload-progress');
 const validos = Array.from(files).filter(f => /\.(pdf|docx)$/i.test(f.name));

 if (validos.length === 0) {
 prog.innerHTML = '<div class="alert alert-error">Solo se aceptan archivos PDF o DOCX.</div>';
 return;
 }

 for (const file of validos) {
 prog.innerHTML = `<div class="alert alert-info"><span class="spinner" style="border-top-color:var(--accent);"></span> Subiendo e indexando <strong>${escHtml(file.name)}</strong>…</div>`;
 try {
 const fd = new FormData();
 fd.append('file', file);
 const r = await fetch(`${API_BASE}/api/admin/upload`, {
 method: 'POST',
 headers: { 'X-Admin-Pin': adminPin },
 body: fd,
 });
 const data = await r.json();
 if (r.ok) {
 prog.innerHTML = `<div class="alert alert-success"><strong>${escHtml(file.name)}</strong> subido. ${data.fragmentos_indexados ?? 0} fragmentos indexados.</div>`;
      marcarCambiosPendientes(true);
    } else {
 prog.innerHTML = `<div class="alert alert-error"> Error al subir <strong>${escHtml(file.name)}</strong>: ${escHtml(data.detail || r.status)}</div>`;
 }
 } catch (e) {
 prog.innerHTML = `<div class="alert alert-error"> Error de red: ${escHtml(e.message)}</div>`;
 }
 await new Promise(r => setTimeout(r, 800));
 }
 cargarDocs();
 setTimeout(() => { prog.innerHTML = ''; }, 4000);
}

// ── BANCO DE PREGUNTAS ───────────────────────────────────────────────
async function cargarPreguntas() {
 const lista = document.getElementById('preguntas-lista');
 const nivel = document.getElementById('filtro-nivel').value;
 lista.innerHTML = '<div style="color:var(--text-muted);padding:20px;text-align:center;"><div class="spinner" style="border-top-color:var(--accent);margin:0 auto 12px;width:24px;height:24px;border-width:3px;"></div></div>';

 try {
 let url = API_BASE + '/api/evaluacion/preguntas?aleatorio=false';
 if (nivel) url += '&nivel=' + encodeURIComponent(nivel);
 const r = await fetch(url);
 if (!r.ok) throw new Error('HTTP ' + r.status);
 const data = await r.json();
 const preguntas = data.preguntas || [];

 if (preguntas.length === 0) {
 lista.innerHTML = '<div class="alert alert-info">No hay preguntas registradas para este nivel.</div>';
 return;
 }

 lista.innerHTML = `
 <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:12px;">${preguntas.length} pregunta${preguntas.length > 1 ? 's' : ''}</p>
 <div class="table-wrap">
 <table>
 <thead>
 <tr>
 <th>#</th>
 <th>ENUNCIADO</th>
 <th>NIVEL</th>
 <th>TEMA</th>
 <th>RESPUESTAS</th>
 <th>ACCIONES</th>
 </tr>
 </thead>
 <tbody>
 ${preguntas.map((q, i) => `
 <tr>
 <td style="color:var(--text-muted);font-size:0.8rem;vertical-align:top;">${i + 1}</td>
 <td style="max-width:340px;color:var(--text-main);vertical-align:top;">${escHtml(q.enunciado)}</td>
 <td style="vertical-align:top;"><span class="badge badge-primary">${escHtml(q.nivel)}</span></td>
 <td style="font-size:0.82rem;color:var(--text-muted);vertical-align:top;">${escHtml(q.tema || '—')}</td>
 <td style="font-size:0.8rem;vertical-align:top;line-height:1.5;">
 ${q.respuestas.map(r => `
 <div style="color:${r.es_correcta ? '#22c55e' : 'var(--text-muted)'};font-weight:${r.es_correcta ? '600' : '400'};margin-bottom:2px;">
 ${r.es_correcta ? ' ' : ''}${escHtml(r.texto)}
 </div>
 `).join('')}
 </td>
 <td style="vertical-align:top;white-space:nowrap;">
 <button class="btn btn-outline" style="font-size:0.75rem;padding:4px 10px;margin-bottom:4px;"
 onclick='abrirModalEditar(${JSON.stringify(q)})'> Editar</button>
 <button class="btn btn-outline" style="font-size:0.75rem;padding:4px 10px;color:#f87171;border-color:#f87171;"
 onclick="eliminarPregunta(${q.id}, ${JSON.stringify(q.enunciado.substring(0,40))})"> Eliminar</button>
 </td>
 </tr>
 `).join('')}
 </tbody>
 </table>
 </div>
 `;

 } catch (e) {
 lista.innerHTML = '<div class="alert alert-error">Error al cargar preguntas: ' + escHtml(e.message) + '</div>';
 }
}

function toggleFormNueva(show) {
 document.getElementById('form-nueva').style.display = show ? 'block' : 'none';
}

async function crearPregunta() {
 const enunciado = document.getElementById('n-enunciado').value.trim();
 const nivel = document.getElementById('n-nivel').value;
 const tema = document.getElementById('n-tema').value.trim();
 const opA = document.getElementById('n-op-a').value.trim();
 const opB = document.getElementById('n-op-b').value.trim();
 const opC = document.getElementById('n-op-c').value.trim();
 const opD = document.getElementById('n-op-d').value.trim();
 const correcta = document.getElementById('n-correcta').value;
 const errDiv = document.getElementById('form-nueva-error');

 if (!enunciado || !opA || !opB || !opC || !opD) {
 errDiv.textContent = 'Completa todos los campos.';
 errDiv.style.display = 'flex';
 return;
 }
 errDiv.style.display = 'none';

 const adminPin = localStorage.getItem('adminPin') || '';
 try {
 const r = await fetch(API_BASE + '/api/admin/preguntas', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json', 'X-Admin-Pin': adminPin },
 body: JSON.stringify({ nivel, tema, enunciado, opcion_a: opA, opcion_b: opB, opcion_c: opC, opcion_d: opD, correcta }),
 });
 const data = await r.json();
 if (!r.ok) throw new Error(data.detail || 'Error al crear pregunta');
 toggleFormNueva(false);
 ['n-enunciado','n-nivel','n-tema','n-op-a','n-op-b','n-op-c','n-op-d'].forEach(id => {
 const el = document.getElementById(id);
 if (el) el.value = id === 'n-nivel' ? 'Principiante' : id === 'n-correcta' ? 'A' : '';
 });
 cargarPreguntas();
 } catch(e) {
 errDiv.textContent = e.message;
 errDiv.style.display = 'flex';
 }
}

async function eliminarPregunta(id, resumen) {
 if (!confirm(`¿Eliminar la pregunta "${resumen}…"?\n\nEsta acción no se puede deshacer.`)) return;
 const adminPin = localStorage.getItem('adminPin') || '';
 try {
 const r = await fetch(API_BASE + '/api/admin/preguntas/' + id, {
 method: 'DELETE',
 headers: { 'X-Admin-Pin': adminPin },
 });
 const data = await r.json();
 if (!r.ok) throw new Error(data.detail || 'Error al eliminar');
 cargarPreguntas();
 } catch(e) {
 alert('Error: ' + e.message);
 }
}

function abrirModalEditar(q) {
 // Rellenar campos del modal con los datos actuales
 document.getElementById('edit-id').value = q.id;
 document.getElementById('edit-enunciado').value = q.enunciado;
 document.getElementById('edit-nivel').value = q.nivel;
 document.getElementById('edit-tema').value = q.tema || '';
 // Mapear respuestas a opciones A,B,C,D
 const opts = ['edit-op-a','edit-op-b','edit-op-c','edit-op-d'];
 let correctaLetra = 'A';
 q.respuestas.forEach((r, idx) => {
 const el = document.getElementById(opts[idx]);
 if (el) el.value = r.texto;
 if (r.es_correcta) correctaLetra = ['A','B','C','D'][idx];
 });
 document.getElementById('edit-correcta').value = correctaLetra;
 document.getElementById('edit-error').style.display = 'none';
 document.getElementById('modal-editar').style.display = 'flex';
}

function cerrarModalEditar() {
 document.getElementById('modal-editar').style.display = 'none';
}

async function guardarEdicionPregunta() {
 const id = document.getElementById('edit-id').value;
 const enunciado = document.getElementById('edit-enunciado').value.trim();
 const nivel = document.getElementById('edit-nivel').value;
 const tema = document.getElementById('edit-tema').value.trim();
 const opA = document.getElementById('edit-op-a').value.trim();
 const opB = document.getElementById('edit-op-b').value.trim();
 const opC = document.getElementById('edit-op-c').value.trim();
 const opD = document.getElementById('edit-op-d').value.trim();
 const correcta = document.getElementById('edit-correcta').value;
 const errDiv = document.getElementById('edit-error');

 if (!enunciado || !opA || !opB || !opC || !opD) {
 errDiv.textContent = 'Completa todos los campos.';
 errDiv.style.display = 'flex';
 return;
 }
 errDiv.style.display = 'none';

 const adminPin = localStorage.getItem('adminPin') || '';
 try {
 const r = await fetch(API_BASE + '/api/admin/preguntas/' + id, {
 method: 'PUT',
 headers: { 'Content-Type': 'application/json', 'X-Admin-Pin': adminPin },
 body: JSON.stringify({ nivel, tema, enunciado, opcion_a: opA, opcion_b: opB, opcion_c: opC, opcion_d: opD, correcta }),
 });
 const data = await r.json();
 if (!r.ok) throw new Error(data.detail || 'Error al actualizar');
 cerrarModalEditar();
 cargarPreguntas();
 } catch(e) {
 errDiv.textContent = e.message;
 errDiv.style.display = 'flex';
 }
}

// ── ESTADÍSTICAS ─────────────────────────────────────────────────────
let _chartNivel = null;
let _chartLatencia = null;
let _statsAllData = []; // cache para filtrado client-side

async function cargarStats() {
 const kpisGrid = document.getElementById('kpis-grid');
 if (!kpisGrid) return;
 kpisGrid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-muted);padding:20px;"><div class="spinner" style="border-top-color:var(--accent);margin:0 auto 10px;width:22px;height:22px;border-width:3px;"></div>Cargando…</div>';

 try {
 const r = await fetch(API_BASE + '/api/admin/stats_sesion', { headers: { 'X-Admin-Pin': adminPin } });
 if (!r.ok) throw new Error('HTTP ' + r.status);
 const d = await r.json();

 _statsAllData = d.recientes || [];

 const total = d.total_consultas || 0;
 const lat = d.lat_prom ? d.lat_prom + 's' : '—';
 const niveles = d.por_nivel || {};
 const temas = d.temas_frecuentes || [];
 const nivEntries = Object.entries(niveles);

 // ── KPIs ──
 kpisGrid.innerHTML =
 kpiCard(total === 0 ? 'Sin actividad' : total, 'Consultas en esta sesión', '#6c3483')
 + kpiCard(lat, 'Tiempo de respuesta promedio', '#1e3a5f')
 + (nivEntries.length > 0
 ? nivEntries.map(([n,c]) => kpiCard(c, 'Nivel ' + _capitalize(n), '#3d2b1f')).join('')
 : kpiCard('—', 'Sin consultas aún', '#444'));

 // ── Temas más consultados ──
 const temasHtml = temas.length > 0
 ? temas.map((t, i) => {
 const pct = Math.round((t.veces / (temas[0]?.veces || 1)) * 100);
 return '<div style="display:flex;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid var(--border);">'
 + '<span style="font-size:0.78rem;color:var(--text-muted);width:16px;text-align:right;flex-shrink:0;">' + (i+1) + '</span>'
 + '<div style="flex:1;">'
 + '<div style="font-size:0.86rem;font-weight:600;color:var(--text-main);text-transform:capitalize;margin-bottom:5px;">' + escHtml(t.tema) + '</div>'
 + '<div style="height:4px;background:var(--border);border-radius:2px;overflow:hidden;">'
 + '<div style="height:100%;width:' + pct + '%;background:var(--accent);border-radius:2px;"></div>'
 + '</div></div>'
 + '<span style="font-size:0.75rem;color:var(--text-muted);flex-shrink:0;">' + t.veces + 'x</span>'
 + '</div>';
 }).join('')
 : '<p style="color:var(--text-muted);font-size:0.83rem;padding:16px 0;text-align:center;margin:0;">Los temas frecuentes aparecerán aquí a medida que los estudiantes usen el asistente.</p>';

 // ── Inyectar sección extra ──
 const extraId = 'stats-extra';
 let extraEl = document.getElementById(extraId);
 if (!extraEl) {
 extraEl = document.createElement('div');
 extraEl.id = extraId;
 kpisGrid.parentElement.appendChild(extraEl);
 }

 extraEl.innerHTML =
 // Fila 1: Temas + Consultas con filtros
 '<div style="display:grid;grid-template-columns:1fr 1.6fr;gap:20px;margin-top:20px;">'
 + '<div class="card" style="display:flex;flex-direction:column;">'
 + '<h3 style="margin-bottom:3px;font-size:0.9rem;font-weight:700;">Temas más consultados</h3>'
 + '<p style="font-size:0.76rem;color:var(--text-muted);margin-bottom:12px;">Palabras clave en las preguntas de los estudiantes.</p>'
 + '<div style="overflow-y:auto;max-height:280px;flex:1;">' + temasHtml + '</div>'
 + '</div>'

 + '<div class="card" style="display:flex;flex-direction:column;">'
 + '<h3 style="margin-bottom:3px;font-size:0.9rem;font-weight:700;">Consultas de la sesión</h3>'
 + '<p style="font-size:0.76rem;color:var(--text-muted);margin-bottom:10px;">Historial completo. Filtra por nivel o palabra clave.</p>'
 // Filtros
 + '<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;">'
 + '<input id="filter-q" type="text" placeholder="Buscar en preguntas…" oninput="_filtrarConsultas()" style="flex:1;min-width:140px;background:var(--bg-input,#fff);border:1px solid var(--border);border-radius:7px;padding:7px 10px;color:var(--text-main);font-size:0.82rem;">'
 + '<select id="filter-nivel" onchange="_filtrarConsultas()" style="background:var(--bg-input,#fff);border:1px solid var(--border);border-radius:7px;padding:7px 10px;color:var(--text-main);font-size:0.82rem;">' 
 + '<option value="">Todos los niveles</option>'
 + '<option value="principiante">Principiante</option>'
 + '<option value="avanzado">Avanzado</option>'
 + '<option value="basico">Básico</option>'
 + '</select>'
 + '</div>'
 + '<div id="consultas-tabla" style="overflow-y:auto;max-height:260px;flex:1;"></div>'
 + '</div>'
 + '</div>'

 // Fila 2: Gráficas
 + '<div style="display:grid;grid-template-columns:1fr 2fr;gap:20px;margin-top:20px;">'
 + '<div class="card">'
 + '<h3 style="margin-bottom:3px;font-size:0.9rem;font-weight:700;">Consultas por nivel</h3>'
 + '<p style="font-size:0.76rem;color:var(--text-muted);margin-bottom:10px;">Distribución según nivel del estudiante.</p>'
 + '<div style="position:relative;height:190px;"><canvas id="chart-nivel-sesion"></canvas></div>'
 + '</div>'
 + '<div class="card">'
 + '<h3 style="margin-bottom:3px;font-size:0.9rem;font-weight:700;">Tiempo de respuesta por consulta</h3>'
 + '<p style="font-size:0.76rem;color:var(--text-muted);margin-bottom:10px;">Segundos que tardó Atena. Barras rojas indican > 4s.</p>'
 + '<div style="position:relative;height:190px;"><canvas id="chart-latencia-sesion"></canvas></div>'
 + '</div>'
 + '</div>';

 // Render tabla inicial sin filtros
 _filtrarConsultas();

 // Gráficas
 const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
 const textColor = isDark ? '#8b949e' : '#64748b';
 const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';

 if (_chartNivel) { _chartNivel.destroy(); _chartNivel = null; }
 const ctxNivel = document.getElementById('chart-nivel-sesion');
 if (ctxNivel && nivEntries.length > 0) {
 _chartNivel = new Chart(ctxNivel, {
 type: 'doughnut',
 data: {
 labels: nivEntries.map(([n]) => _capitalize(n)),
 datasets: [{ data: nivEntries.map(([,c]) => c), backgroundColor: ['#6c3483','#8CC63F','#1e3a5f','#b7950b'], borderWidth: 0 }]
 },
 options: {
 responsive: true, maintainAspectRatio: false, cutout: '60%',
 plugins: { legend: { position: 'bottom', labels: { color: textColor, font: { size: 11, family: 'Outfit' }, padding: 10 } } }
 }
 });
 } else if (ctxNivel) {
 ctxNivel.parentElement.innerHTML = '<p style="color:var(--text-muted);font-size:0.82rem;text-align:center;padding:60px 0;margin:0;">Sin datos aún</p>';
 }

 if (_chartLatencia) { _chartLatencia.destroy(); _chartLatencia = null; }
 const ctxLat = document.getElementById('chart-latencia-sesion');
 const latData = [..._statsAllData].reverse();
 if (ctxLat && latData.length > 0) {
 _chartLatencia = new Chart(ctxLat, {
 type: 'bar',
 data: {
 labels: latData.map((q, i) => '#' + (i + 1)),
 datasets: [{ label: 'Segundos', data: latData.map(q => q.latencia || 0),
 backgroundColor: latData.map(q => (q.latencia || 0) > 4 ? 'rgba(239,68,68,0.7)' : 'rgba(108,52,131,0.7)'),
 borderRadius: 5, borderSkipped: false }]
 },
 options: {
 responsive: true, maintainAspectRatio: false,
 plugins: { legend: { display: false },
 tooltip: { callbacks: {
 title: (items) => { const q = latData[items[0].dataIndex]; return q ? q.pregunta.substring(0,50)+'…' : ''; },
 label: (item) => ' ' + item.raw + 's'
 }}},
 scales: {
 x: { grid: { display: false }, ticks: { color: textColor, font: { size: 10 } } },
 y: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 10 }, callback: v => v+'s' }, beginAtZero: true }
 }
 }
 });
 } else if (ctxLat) {
 ctxLat.parentElement.innerHTML = '<p style="color:var(--text-muted);font-size:0.82rem;text-align:center;padding:60px 0;margin:0;">Sin datos aún</p>';
 }

 } catch (e) {
 kpisGrid.innerHTML = '<div class="alert alert-error" style="grid-column:1/-1;">No se pudieron cargar las estadísticas: ' + escHtml(e.message) + '</div>';
 }
}

function _filtrarConsultas() {
 const q = (document.getElementById('filter-q')?.value || '').toLowerCase().trim();
 const nivel = (document.getElementById('filter-nivel')?.value || '').toLowerCase();
 const tbody = document.getElementById('consultas-tabla');
 if (!tbody) return;

 const filtradas = _statsAllData.filter(c => {
 const matchQ = !q || (c.pregunta || '').toLowerCase().includes(q);
 const matchNivel = !nivel || (c.nivel || '').toLowerCase().includes(nivel);
 return matchQ && matchNivel;
 });

 if (filtradas.length === 0) {
 tbody.innerHTML = '<p style="color:var(--text-muted);font-size:0.82rem;padding:20px 0;text-align:center;margin:0;">'
 + (q || nivel ? 'Sin resultados para ese filtro.' : 'Las consultas aparecerán aquí en tiempo real.') + '</p>';
 return;
 }

 tbody.innerHTML = '<table style="width:100%;border-collapse:collapse;font-size:0.82rem;">'
 + '<thead><tr>'
 + ['Hora','Pregunta','Nivel','Resp.'].map((h, i) =>
 '<th style="text-align:' + (i===3?'right':'left') + ';padding:7px 8px;border-bottom:1px solid var(--border);color:var(--text-muted);font-weight:600;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.04em;white-space:nowrap;">' + h + '</th>'
 ).join('')
 + '</tr></thead><tbody>'
 + filtradas.map(c =>
 '<tr>'
 + '<td style="padding:8px;border-bottom:1px solid var(--border);white-space:nowrap;color:var(--text-muted);font-size:0.78rem;">' + escHtml((c.fecha||'').replace('T',' ').substring(5,16)) + '</td>'
 + '<td style="padding:8px;border-bottom:1px solid var(--border);color:var(--text-main);max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + escHtml(c.pregunta||'') + '">' + escHtml(c.pregunta||'') + '</td>'
 + '<td style="padding:8px;border-bottom:1px solid var(--border);"><span class="badge badge-primary" style="font-size:0.68rem;">' + escHtml(_capitalize(c.nivel||'—')) + '</span></td>'
 + '<td style="padding:8px;border-bottom:1px solid var(--border);text-align:right;color:var(--text-muted);">' + (c.latencia!=null?c.latencia+'s':'—') + '</td>'
 + '</tr>'
 ).join('')
 + '</tbody></table>';
}

function _capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }

function kpiCard(value, label, color) {
 return '<div class="kpi-card" style="border-top:3px solid ' + color + ';">'
 + '<div class="kpi-value" style="color:' + color + ';font-size:1.25rem;font-weight:800;">' + escHtml(String(value)) + '</div>'
 + '<div class="kpi-label" style="margin-top:4px;font-size:0.74rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.04em;">' + label + '</div>'
 + '</div>';
}


// ── SISTEMA ───────────────────────────────────────────────────────────
async function cargarSistema() {
 const container = document.getElementById('sistema-info');
 container.innerHTML = '<div style="color:var(--text-muted);padding:20px;text-align:center;"><div class="spinner" style="border-top-color:var(--accent);margin:0 auto 12px;width:24px;height:24px;border-width:3px;"></div>Verificando…</div>';

 function statusCard(ok, emoji, titulo, descripcionOk, descripcionFalla, accion) {
 const color = ok ? '#22c55e' : '#f59e0b';
 const bg = ok ? 'rgba(34,197,94,0.06)' : 'rgba(245,158,11,0.06)';
 const borde = ok ? 'rgba(34,197,94,0.2)' : 'rgba(245,158,11,0.25)';
 return '<div style="display:flex;align-items:flex-start;gap:14px;padding:14px 18px;background:' + bg + ';border:1px solid ' + borde + ';border-radius:12px;">'
 + '<div style="font-size:1.5rem;line-height:1;margin-top:2px;">' + emoji + '</div>'
 + '<div style="flex:1;">'
 + '<div style="font-weight:700;font-size:0.92rem;color:var(--text-main);margin-bottom:3px;">' + titulo + '</div>'
 + '<div style="font-size:0.8rem;color:var(--text-muted);">' + (ok ? descripcionOk : descripcionFalla) + '</div>'
 + ((!ok && accion) ? '<div style="margin-top:8px;font-size:0.78rem;padding:6px 10px;background:rgba(245,158,11,0.1);border-radius:6px;color:#f59e0b;">' + accion + '</div>' : '')
 + '</div>'
 + '<div style="font-size:0.75rem;font-weight:600;color:' + color + ';white-space:nowrap;margin-top:2px;">' + (ok ? '● Activo' : '● Revisar') + '</div>'
 + '</div>';
 }

 try {
 const [rSalud, rDiag] = await Promise.all([
 fetch(API_BASE + '/salud'),
 fetch(API_BASE + '/diagnostico/db', { headers: { 'X-Admin-Pin': localStorage.getItem('adminPin') || '' } }).catch(() => null),
 ]);

 const salud = rSalud.ok ? await rSalud.json() : null;
 const diag = rDiag && rDiag.ok ? await rDiag.json() : null;

 const online = salud && salud.estado === 'ok';
 const iaLista = salud && salud.vector_store_listo;
 const dbOk = diag && diag.conexion === 'ok';
 const totalPreguntas = dbOk ? Object.values(diag.niveles || {}).reduce((a, v) => a + v, 0) : null;

 const nivelesBadges = (dbOk && diag.niveles)
 ? '<div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;">'
 + Object.entries(diag.niveles).map(([n,c]) =>
 '<span class="badge badge-primary" style="font-size:0.72rem;">' + escHtml(n) + ': ' + c + ' preguntas</span>'
 ).join('') + '</div>'
 : '';

 container.innerHTML =
 // ── Encabezado ──
 '<div class="card" style="grid-column:1/-1;">'
 + '<div style="display:flex;align-items:center;gap:14px;margin-bottom:22px;">'
 + '<div style="width:50px;height:50px;border-radius:14px;background:linear-gradient(135deg,#4a235a,#6c3483);display:flex;align-items:center;justify-content:center;font-family:Outfit,sans-serif;font-weight:800;font-size:1.25rem;color:#fff;">A</div>'
 + '<div><div style="font-family:Outfit,sans-serif;font-weight:700;font-size:1rem;color:var(--text-main);">Atena — Asistente de Neuroanatomía</div>'
 + '<div style="font-size:0.78rem;color:var(--text-muted);">Laboratorio de Neuropsicología · Konrad Lorenz</div></div>'
 + '<div style="margin-left:auto;padding:5px 14px;border-radius:20px;font-size:0.78rem;font-weight:600;'
 + 'background:' + (online ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)') + ';'
 + 'color:' + (online ? '#22c55e' : '#ef4444') + ';'
 + 'border:1px solid ' + (online ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)') + ';'
 + '">' + (online ? '● Funcionando' : '● Sin respuesta') + '</div>'
 + '</div>'
 + '<div style="display:flex;flex-direction:column;gap:10px;">'

 + statusCard(
 online,
 '',
 'Atena disponible para los estudiantes',
 'El asistente está en línea y puede responder consultas en este momento.',
 'El asistente no está respondiendo. Verifica que el servidor esté encendido.',
 'Contacta al administrador técnico o reinicia el servidor.'
 )

 + statusCard(
 iaLista,
 '',
 'Material de estudio cargado',
 'Los libros y documentos de neuroanatomía están disponibles para consulta.',
 'No hay material de estudio cargado. Las respuestas serán limitadas.',
 'Ve a la sección "Documentos" y sube los PDFs del curso.'
 )

 + statusCard(
 dbOk,
 '',
 'Banco de evaluaciones' + (totalPreguntas ? ' (' + totalPreguntas + ' preguntas)' : ''),
 'Las preguntas de autoevaluación están disponibles para los estudiantes.' + (nivelesBadges || ''),
 'El banco de preguntas no está disponible en este momento.',
 'Esto puede ser temporal. Si persiste, entra a supabase.com y reactiva el proyecto "Atena".'
 )

 + '</div></div>'

 // ── Tarjeta cambio de PIN ──
 + '<div class="card">'
 + '<h3 style="margin-bottom:6px;font-size:0.95rem;"> Cambiar contraseña de acceso</h3>'
 + '<p style="font-size:0.78rem;color:var(--text-muted);margin-bottom:14px;">Cambia el PIN que usas para entrar a este panel de administración.</p>'
 + '<div style="display:flex;flex-direction:column;gap:10px;">'
 + '<div><label style="font-size:0.78rem;color:var(--text-muted);display:block;margin-bottom:4px;">CONTRASEÑA ACTUAL</label>'
 + '<input type="password" id="pin-actual" placeholder="••••••" style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text-main);font-size:0.88rem;box-sizing:border-box;"></div>'
 + '<div><label style="font-size:0.78rem;color:var(--text-muted);display:block;margin-bottom:4px;">NUEVA CONTRASEÑA</label>'
 + '<input type="password" id="pin-nuevo" placeholder="Mínimo 4 caracteres" style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text-main);font-size:0.88rem;box-sizing:border-box;"></div>'
 + '<div><label style="font-size:0.78rem;color:var(--text-muted);display:block;margin-bottom:4px;">CONFIRMAR NUEVA CONTRASEÑA</label>'
 + '<input type="password" id="pin-confirmar" placeholder="Repite la nueva contraseña" style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text-main);font-size:0.88rem;box-sizing:border-box;"></div>'
 + '<div id="pin-msg" style="display:none;font-size:0.82rem;padding:8px 12px;border-radius:6px;"></div>'
 + '<button class="btn btn-primary" onclick="cambiarPin()" style="font-size:0.85rem;"> Actualizar contraseña</button>'
 + '</div></div>'

 // ── Tarjeta accesos directos ──
 + '<div class="card">'
 + '<h3 style="margin-bottom:6px;font-size:0.95rem;"> Accesos directos</h3>'
 + '<p style="font-size:0.78rem;color:var(--text-muted);margin-bottom:14px;">Navega rápidamente a las secciones del panel.</p>'
 + '<div style="display:flex;flex-direction:column;gap:8px;">'
 + '<button class="btn btn-outline" onclick="cargarSistema()" style="font-size:0.84rem;text-align:left;">↺ Actualizar estado</button>'
 + '<button class="btn btn-outline" onclick="showSection(\'docs\', document.querySelectorAll(\'.sidebar-item\')[0])" style="font-size:0.84rem;text-align:left;"> Gestionar documentos del curso</button>'
 + '<button class="btn btn-outline" onclick="showSection(\'preguntas\', document.querySelectorAll(\'.sidebar-item\')[1])" style="font-size:0.84rem;text-align:left;"> Banco de preguntas de evaluación</button>'
 + '<button class="btn btn-outline" onclick="showSection(\'stats\', document.querySelectorAll(\'.sidebar-item\')[2])" style="font-size:0.84rem;text-align:left;"> Estadísticas de uso del laboratorio</button>'
 + '</div></div>';

 } catch (e) {
 container.innerHTML = '<div class="alert alert-error">No fue posible verificar el estado de Atena. Asegúrate de que el servidor esté encendido.<br><small style="opacity:0.6;">' + escHtml(e.message) + '</small></div>';
 }
}

async function cambiarPin() {
  const actual    = document.getElementById('pin-actual').value.trim();
  const nuevo     = document.getElementById('pin-nuevo').value.trim();
  const confirmar = document.getElementById('pin-confirmar').value.trim();
  const msg       = document.getElementById('pin-msg');

  function showMsg(text, ok) {
    msg.textContent = text;
    msg.style.display = 'block';
    msg.style.background = ok ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)';
    msg.style.color = ok ? '#22c55e' : '#ef4444';
    msg.style.border = '1px solid ' + (ok ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)');
  }

  if (!actual || !nuevo || !confirmar) return showMsg('Completa todos los campos.', false);
  if (nuevo.length < 4) return showMsg('El nuevo PIN debe tener al menos 4 caracteres.', false);
  if (nuevo !== confirmar) return showMsg('El nuevo PIN y la confirmación no coinciden.', false);

  try {
    const r = await fetch(API_BASE + '/api/admin/cambiar-pin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Pin': actual },
      body: JSON.stringify({ pin_actual: actual, pin_nuevo: nuevo }),
    });
    const data = await r.json();
    if (!r.ok) return showMsg(data.detail || 'PIN actual incorrecto.', false);
    // Actualizar el PIN guardado localmente para que las peticiones sigan funcionando
    localStorage.setItem('adminPin', nuevo);
    document.getElementById('pin-actual').value = '';
    document.getElementById('pin-nuevo').value = '';
    document.getElementById('pin-confirmar').value = '';
    showMsg('PIN actualizado correctamente. Usa el nuevo PIN en tu próximo ingreso.', true);
  } catch(e) {
    showMsg('Error de red: ' + e.message, false);
  }
}

// ── Init ─────────────────────────────────────────────────────────────
(function init() {
 initTheme();

 // Inyectar modal de edición de preguntas (una sola vez al cargar la página)
 if (!document.getElementById('modal-editar')) {
 const modalHtml = `
 <div id="modal-editar" style="display:none;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.6);align-items:center;justify-content:center;">
 <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:28px 32px;width:min(560px,95vw);max-height:90vh;overflow-y:auto;box-shadow:0 8px 40px rgba(0,0,0,0.5);">
 <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
 <h3 style="font-size:1.05rem;font-weight:700;color:var(--text-main);"> Editar Pregunta</h3>
 <button onclick="cerrarModalEditar()" style="background:none;border:none;color:var(--text-muted);font-size:1.4rem;cursor:pointer;line-height:1;">×</button>
 </div>
 <input type="hidden" id="edit-id">
 <div style="display:flex;flex-direction:column;gap:12px;">
 <div>
 <label style="font-size:0.8rem;color:var(--text-muted);display:block;margin-bottom:4px;">ENUNCIADO</label>
 <textarea id="edit-enunciado" rows="3" style="width:100%;resize:vertical;background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:10px;color:var(--text-main);font-size:0.9rem;"></textarea>
 </div>
 <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
 <div>
 <label style="font-size:0.8rem;color:var(--text-muted);display:block;margin-bottom:4px;">NIVEL</label>
 <select id="edit-nivel" style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:9px 10px;color:var(--text-main);font-size:0.88rem;">
 <option>Principiante</option>
 <option>Avanzado</option>
 <option>General</option>
 </select>
 </div>
 <div>
 <label style="font-size:0.8rem;color:var(--text-muted);display:block;margin-bottom:4px;">TEMA</label>
 <input type="text" id="edit-tema" placeholder="Ej: Hipocampo" style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:9px 10px;color:var(--text-main);font-size:0.88rem;">
 </div>
 </div>
 <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
 <div><label style="font-size:0.78rem;color:var(--text-muted);display:block;margin-bottom:3px;">OPCIÓN A</label><input type="text" id="edit-op-a" style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:8px 10px;color:var(--text-main);font-size:0.86rem;"></div>
 <div><label style="font-size:0.78rem;color:var(--text-muted);display:block;margin-bottom:3px;">OPCIÓN B</label><input type="text" id="edit-op-b" style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:8px 10px;color:var(--text-main);font-size:0.86rem;"></div>
 <div><label style="font-size:0.78rem;color:var(--text-muted);display:block;margin-bottom:3px;">OPCIÓN C</label><input type="text" id="edit-op-c" style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:8px 10px;color:var(--text-main);font-size:0.86rem;"></div>
 <div><label style="font-size:0.78rem;color:var(--text-muted);display:block;margin-bottom:3px;">OPCIÓN D</label><input type="text" id="edit-op-d" style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:8px 10px;color:var(--text-main);font-size:0.86rem;"></div>
 </div>
 <div>
 <label style="font-size:0.8rem;color:var(--text-muted);display:block;margin-bottom:4px;">RESPUESTA CORRECTA</label>
 <select id="edit-correcta" style="background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:9px 10px;color:var(--text-main);font-size:0.88rem;">
 <option value="A">A</option>
 <option value="B">B</option>
 <option value="C">C</option>
 <option value="D">D</option>
 </select>
 </div>
 <div id="edit-error" class="alert alert-error" style="display:none;font-size:0.85rem;padding:10px 14px;"></div>
 <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px;">
 <button class="btn btn-outline" onclick="cerrarModalEditar()" style="font-size:0.88rem;">Cancelar</button>
 <button class="btn btn-primary" onclick="guardarEdicionPregunta()" style="font-size:0.88rem;"> Guardar cambios</button>
 </div>
 </div>
 </div>
 </div>
 `;
 document.body.insertAdjacentHTML('beforeend', modalHtml);
 }

 // Mantener sesión al recargar la página si ya se autenticó previamente
 const savedPin = sessionStorage.getItem('atena_admin_pin');
 const loginScr = document.getElementById('login-screen');
 const adminPnl = document.getElementById('admin-panel');
 if (savedPin) {
 adminPin = savedPin;
 localStorage.setItem('adminPin', savedPin);
 if (loginScr) loginScr.style.display = 'none';
 if (adminPnl) adminPnl.style.display = 'flex';
 cargarDocs();
 } else {
 adminPin = '';
 if (loginScr) loginScr.style.display = 'flex';
 if (adminPnl) adminPnl.style.display = 'none';
 const pinInput = document.getElementById('pin-input');
 if (pinInput) {
 pinInput.value = '';
 setTimeout(function () { pinInput.focus(); }, 150);
 }
 }
})();


// ── Vista previa Autoevaluación en Admin ─────────────────────────────
let adminQuizPreguntas = [], adminQuizIndice = 0, adminQuizAciertos = 0, adminQuizNivel = 'Principiante';

function abrirQuizAdmin() {
  adminQuizPreguntas = []; adminQuizIndice = 0; adminQuizAciertos = 0;
  const content = document.getElementById('admin-quiz-content');
  if (!content) return;

  const niveles = [
    { key: 'Principiante', desc: 'Conceptos fundamentales' },
    { key: 'General',      desc: 'Conocimiento intermedio' },
    { key: 'Avanzado',     desc: 'Profundización clínica' },
  ];
  const botones = niveles.map(n => `
    <button onclick="iniciarQuizAdmin('${n.key}')"
      style="width:100%;text-align:left;background:var(--bg-input);border:1px solid var(--border);
             border-radius:10px;padding:14px 18px;margin-bottom:10px;cursor:pointer;
             transition:border-color .2s,transform .1s;color:var(--text-main);"
      onmouseover="this.style.borderColor='var(--accent)';this.style.transform='translateX(3px)'"
      onmouseout="this.style.borderColor='var(--border)';this.style.transform=''">
      <strong style="display:block;margin-bottom:2px;">${n.key}</strong>
      <span style="font-size:0.82rem;color:var(--text-muted);">${n.desc}</span>
    </button>`).join('');

  content.innerHTML = `
    <p style="color:var(--text-muted);font-size:0.88rem;margin-bottom:18px;">
      Selecciona el nivel para previsualizar:
    </p>
    ${botones}
    <button onclick="iniciarQuizAdmin('todos')"
      style="width:100%;text-align:left;background:transparent;border:1px dashed var(--border);
             border-radius:10px;padding:14px 18px;cursor:pointer;color:var(--text-muted);transition:border-color .2s;"
      onmouseover="this.style.borderColor='var(--accent)'"
      onmouseout="this.style.borderColor='var(--border)'">
      <strong style="display:block;color:var(--text-main);margin-bottom:2px;">Todos los niveles</strong>
      <span style="font-size:0.82rem;">Mezcla aleatoria</span>
    </button>`;
}

async function iniciarQuizAdmin(nivel) {
  adminQuizNivel = nivel;
  adminQuizPreguntas = []; adminQuizIndice = 0; adminQuizAciertos = 0;
  const content = document.getElementById('admin-quiz-content');
  const nivelParam = nivel !== 'todos' ? `&nivel=${encodeURIComponent(nivel)}` : '';
  content.innerHTML = `<div style="text-align:center;padding:32px;color:var(--text-muted);">
    <div class="spinner" style="border-top-color:var(--accent);margin:0 auto 12px;width:24px;height:24px;border-width:3px;"></div>
    Cargando preguntas de ${nivel === 'todos' ? 'todos los niveles' : nivel}…</div>`;
  try {
    const r = await fetch(`${API_BASE}/api/evaluacion/preguntas?cantidad=10&aleatorio=true${nivelParam}`, {
      headers: { 'X-Admin-Pin': adminPin }
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    if (!data.preguntas || data.preguntas.length === 0) {
      content.innerHTML = `<p style="text-align:center;color:var(--text-muted);">No hay preguntas para este nivel.<br>
        <small>Agrégalas en la sección Banco de Preguntas.</small></p>`;
      return;
    }
    adminQuizPreguntas = data.preguntas;
    renderAdminPregunta();
  } catch(e) {
    content.innerHTML = `<p style="text-align:center;color:#ef4444;">Error al cargar: ${e.message}</p>`;
  }
}

function renderAdminPregunta() {
  const q = adminQuizPreguntas[adminQuizIndice];
  const total = adminQuizPreguntas.length;
  const content = document.getElementById('admin-quiz-content');
  const opcs = q.respuestas.map((r,i) => `
    <button id="adm-opt-${i}" onclick="responderAdmin(${i},${r.es_correcta})"
      style="width:100%;text-align:left;padding:12px 16px;margin-bottom:8px;
             background:var(--bg-input);border:1px solid var(--border);border-radius:9px;
             cursor:pointer;color:var(--text-main);font-size:0.9rem;transition:border-color .15s;"
      onmouseover="this.style.borderColor='var(--accent)'" onmouseout="this.style.borderColor='var(--border)'">
      ${r.texto}
    </button>`).join('');
  content.innerHTML = `
    <div style="font-size:0.78rem;color:var(--accent);font-weight:600;margin-bottom:6px;letter-spacing:.05em;">
      PREGUNTA ${adminQuizIndice+1} DE ${total} · ${q.nivel?.toUpperCase()} · ${q.tema || ''}
    </div>
    <p style="font-size:1rem;font-weight:500;margin-bottom:18px;">${q.enunciado}</p>
    <div id="adm-opciones">${opcs}</div>
    <div id="adm-feedback" style="display:none;margin-top:14px;padding:12px 16px;border-radius:9px;font-size:0.88rem;"></div>`;
}

function responderAdmin(idx, esCorrecta) {
  document.querySelectorAll('[id^="adm-opt-"]').forEach(b => b.disabled = true);
  const fb = document.getElementById('adm-feedback');
  if (esCorrecta) {
    adminQuizAciertos++;
    fb.style.cssText = 'display:block;background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.35);border-radius:9px;padding:12px 16px;margin-top:14px;font-size:0.88rem;color:#22c55e;';
    fb.textContent = 'Correcto.';
  } else {
    fb.style.cssText = 'display:block;background:rgba(239,68,68,0.10);border:1px solid rgba(239,68,68,0.35);border-radius:9px;padding:12px 16px;margin-top:14px;font-size:0.88rem;color:#ef4444;';
    const correcta = adminQuizPreguntas[adminQuizIndice].respuestas.find(r => r.es_correcta);
    fb.textContent = `Incorrecto. Respuesta correcta: ${correcta?.texto || ''}`;
  }
  const siguiente = adminQuizIndice + 1 < adminQuizPreguntas.length;
  const btnLabel = siguiente ? 'Siguiente' : 'Ver resultado';
  const content = document.getElementById('admin-quiz-content');
  const btn = document.createElement('button');
  btn.className = 'btn btn-primary';
  btn.style.marginTop = '14px';
  btn.textContent = btnLabel;
  btn.onclick = () => {
    adminQuizIndice++;
    if (adminQuizIndice < adminQuizPreguntas.length) {
      renderAdminPregunta();
    } else {
      const pct = Math.round(adminQuizAciertos / adminQuizPreguntas.length * 100);
      document.getElementById('admin-quiz-content').innerHTML = `
        <div style="text-align:center;padding:20px;">
          <div style="font-size:2.5rem;font-weight:700;color:var(--accent);">${pct}%</div>
          <p style="color:var(--text-muted);margin-top:8px;">${adminQuizAciertos} de ${adminQuizPreguntas.length} correctas</p>
          <button class="btn btn-primary" style="margin-top:18px;" onclick="abrirQuizAdmin()">Volver a intentar</button>
        </div>`;
    }
  };
  fb.after(btn);
}
