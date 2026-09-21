/* ═══════════════════════════════════════════════════════════════════
   admin.js — Panel de Administración de Atena
   Gestión de documentos, preguntas, estadísticas y sistema.
   ═══════════════════════════════════════════════════════════════════ */

const API_BASE = '';
let adminPin = '';
let chartVolumen = null;
let chartNiveles = null;

// ── Dark mode (compartido con app.js) ────────────────────────────────
function initTheme() {
  const saved = localStorage.getItem('atena_theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
}
function toggleTheme() {
  const cur = document.documentElement.getAttribute('data-theme');
  const next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('atena_theme', next);
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
  document.getElementById('admin-panel').style.display = 'none';
  document.getElementById('login-screen').style.display = 'flex';
  document.getElementById('pin-input').value = '';
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
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function fmtFecha(iso) {
  try {
    return new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' });
  } catch { return iso; }
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
      <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:12px;">${docs.length} documento${docs.length>1?'s':''} indexado${docs.length>1?'s':''}</p>
      ${docs.map(d => {
        const ext = (d.nombre.split('.').pop() || 'DOC').toUpperCase();
        const nombre = d.nombre.replace(/_/g,' ').replace(/\.(pdf|docx)$/i,'');
        return `
          <div class="card card-accent" style="display:flex;align-items:center;gap:14px;padding:13px 18px;margin-bottom:8px;">
            <span class="badge badge-accent">${ext}</span>
            <div style="flex:1;overflow:hidden;">
              <div style="font-weight:600;font-size:0.92rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escHtml(nombre)}</div>
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
  if (!confirm(`¿Eliminar "${nombre.replace(/_/g,' ')}"?\nEsta acción no se puede deshacer.`)) return;
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
      alert(`✅ Reindexado. ${data.total_vectores ?? '?'} vectores generados.`);
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
        prog.innerHTML = `<div class="alert alert-success">✅ <strong>${escHtml(file.name)}</strong> subido. ${data.fragmentos_indexados ?? 0} fragmentos indexados.</div>`;
      } else {
        prog.innerHTML = `<div class="alert alert-error">❌ Error al subir <strong>${escHtml(file.name)}</strong>: ${escHtml(data.detail || r.status)}</div>`;
      }
    } catch (e) {
      prog.innerHTML = `<div class="alert alert-error">❌ Error de red: ${escHtml(e.message)}</div>`;
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
    let url = `${API_BASE}/api/evaluacion/preguntas?aleatorio=false`;
    if (nivel) url += `&nivel=${encodeURIComponent(nivel)}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    const preguntas = data.preguntas || [];

    if (preguntas.length === 0) {
      lista.innerHTML = '<div class="alert alert-info">No hay preguntas registradas para este nivel.</div>';
      return;
    }

    lista.innerHTML = `
      <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:12px;">${preguntas.length} pregunta${preguntas.length>1?'s':''}</p>
      <div class="table-wrap">
        <table>
          <thead><tr><th>#</th><th>Enunciado</th><th>Nivel</th><th>Tema</th><th>Respuestas</th></tr></thead>
          <tbody>
            ${preguntas.map((q, i) => {
              const correcta = q.respuestas.find(r => r.es_correcta);
              return `<tr>
                <td style="color:var(--text-muted);font-size:0.8rem;">${i+1}</td>
                <td style="max-width:340px;">${escHtml(q.enunciado)}</td>
                <td><span class="badge badge-primary">${escHtml(q.nivel)}</span></td>
                <td style="font-size:0.82rem;color:var(--text-muted);">${escHtml(q.tema || '—')}</td>
                <td style="font-size:0.8rem;">
                  ${q.respuestas.map(r => `
                    <span style="color:${r.es_correcta ? '#22c55e' : 'var(--text-muted)'};">${r.es_correcta?'✓':''} ${escHtml(r.texto.substring(0,40))}${r.texto.length>40?'…':''}</span><br>
                  `).join('')}
                </td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (e) {
    lista.innerHTML = `<div class="alert alert-error">Error al cargar preguntas: ${escHtml(e.message)}</div>`;
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

  // Nota: el endpoint de creación de preguntas requiere la implementación
  // en el backend. Por ahora mostramos un mensaje informativo.
  errDiv.style.display = 'none';
  alert('Funcionalidad de creación de preguntas: se implementará en el endpoint POST /api/admin/preguntas.\n\nPor ahora usa Supabase directamente para agregar preguntas.');
}

// ── ESTADÍSTICAS ─────────────────────────────────────────────────────
async function cargarStats() {
  const dias = document.getElementById('filtro-dias')?.value || 30;
  const kpisGrid = document.getElementById('kpis-grid');
  const recientesBody = document.getElementById('recientes-body');

  kpisGrid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-muted);padding:20px;">Cargando estadísticas…</div>';

  try {
    const r = await fetch(`${API_BASE}/api/admin/metricas?dias=${dias}`, {
      headers: { 'X-Admin-Pin': adminPin }
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();

    const k = data.kpis || {};
    const kpis = [
      { label: 'Consultas totales', value: k.total_consultas ?? 0, color: '#4a235a' },
      { label: 'Latencia prom.', value: k.latencia_promedio ? `${k.latencia_promedio}s` : '—', color: '#1e3a5f' },
      { label: 'Evaluaciones', value: k.total_evaluaciones ?? 0, color: '#14532d' },
      { label: 'Precisión global', value: k.total_evaluaciones ? `${k.porcentaje_aciertos}%` : '—', color: '#7c2d12' },
      { label: 'Respuestas correctas', value: k.evaluaciones_correctas ?? 0, color: '#4a235a' },
    ];

    kpisGrid.innerHTML = kpis.map(kpi => `
      <div class="kpi-card" style="border-top-color:${kpi.color};">
        <div class="kpi-label">${kpi.label}</div>
        <div class="kpi-value" style="color:${kpi.color};">${kpi.value}</div>
      </div>
    `).join('');

    // Gráfico volumen diario
    renderChartVolumen(data.volumen_diario || []);
    // Gráfico distribución por nivel
    renderChartNiveles(data.distribucion || {});
    // Tabla recientes
    renderRecientes(data.recientes || []);

  } catch (e) {
    kpisGrid.innerHTML = `<div class="alert alert-error" style="grid-column:1/-1;">No se pudieron cargar las estadísticas: ${escHtml(e.message)}</div>`;
  }
}

function renderChartVolumen(volumen) {
  const ctx = document.getElementById('chart-volumen');
  if (!ctx) return;
  if (chartVolumen) { chartVolumen.destroy(); chartVolumen = null; }

  if (volumen.length === 0) {
    ctx.parentElement.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:0.88rem;">Sin consultas en este período</div>';
    return;
  }

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const textColor = isDark ? '#8b949e' : '#64748b';
  const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';

  chartVolumen = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: volumen.map(v => {
        try { return new Date(v.dia).toLocaleDateString('es-CO', { month:'short', day:'numeric' }); }
        catch { return v.dia; }
      }),
      datasets: [{
        label: 'Consultas',
        data: volumen.map(v => v.total),
        backgroundColor: '#8CC63F',
        borderRadius: 5,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, title: { display: true, text: 'Consultas por día', color: textColor, font: { size: 13, family: 'Outfit' } } },
      scales: {
        x: { grid: { display: false }, ticks: { color: textColor, font: { size: 11 } } },
        y: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 11 } }, beginAtZero: true },
      },
    }
  });
}

function renderChartNiveles(dist) {
  const ctx = document.getElementById('chart-niveles');
  if (!ctx) return;
  if (chartNiveles) { chartNiveles.destroy(); chartNiveles = null; }

  const keys = Object.keys(dist);
  if (keys.length === 0) {
    ctx.parentElement.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:0.88rem;">Sin datos por nivel</div>';
    return;
  }

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const textColor = isDark ? '#8b949e' : '#64748b';

  chartNiveles = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: keys,
      datasets: [{
        data: keys.map(k => dist[k]),
        backgroundColor: ['#4a235a', '#8CC63F', '#6c3483', '#7ab332'],
        borderWidth: 2,
        borderColor: isDark ? '#161b22' : '#ffffff',
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '55%',
      plugins: {
        legend: { position: 'bottom', labels: { color: textColor, font: { size: 11 } } },
        title: { display: true, text: 'Por nivel', color: textColor, font: { size: 13, family: 'Outfit' } },
      },
    }
  });
}

function renderRecientes(recientes) {
  const tbody = document.getElementById('recientes-body');
  if (!tbody) return;
  if (recientes.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);">Sin registros</td></tr>';
    return;
  }
  tbody.innerHTML = recientes.map(r => `
    <tr>
      <td style="white-space:nowrap;font-size:0.8rem;">${fmtFecha(r.fecha)}</td>
      <td style="max-width:320px;font-size:0.85rem;">${escHtml(r.pregunta.substring(0,90))}${r.pregunta.length>90?'…':''}</td>
      <td><span class="badge badge-primary">${escHtml(r.nivel)}</span></td>
      <td style="font-size:0.82rem;color:var(--text-muted);">${r.latencia ? r.latencia.toFixed(2)+'s' : '—'}</td>
    </tr>
  `).join('');
}

// ── SISTEMA ──────────────────────────────────────────────────────────
async function cargarSistema() {
  const container = document.getElementById('sistema-info');
  container.innerHTML = '<div style="color:var(--text-muted);padding:20px;">Cargando información del sistema…</div>';

  try {
    const [rSalud, rInfo] = await Promise.all([
      fetch(`${API_BASE}/salud`),
      fetch(`${API_BASE}/info`),
    ]);
    const salud = rSalud.ok ? await rSalud.json() : null;
    const info = rInfo.ok ? await rInfo.json() : null;

    container.innerHTML = `
      <div class="card">
        <h3 style="margin-bottom:12px;">Estado del Servicio</h3>
        <div style="display:flex;flex-direction:column;gap:8px;font-size:0.88rem;">
          <div style="display:flex;justify-content:space-between;">
            <span style="color:var(--text-muted);">Estado API</span>
            <span style="color:${salud ? '#22c55e' : '#ef4444'};font-weight:600;">${salud ? '✅ Activo' : '❌ Sin respuesta'}</span>
          </div>
          ${salud ? `
          <div style="display:flex;justify-content:space-between;">
            <span style="color:var(--text-muted);">Vector store</span>
            <span style="font-weight:600;">${salud.vector_store ?? '?'}</span>
          </div>
          <div style="display:flex;justify-content:space-between;">
            <span style="color:var(--text-muted);">Documentos indexados</span>
            <span style="font-weight:600;">${salud.documentos_indexados ?? '?'}</span>
          </div>
          ` : ''}
        </div>
      </div>
      <div class="card">
        <h3 style="margin-bottom:12px;">Modelos y Configuración</h3>
        <div style="display:flex;flex-direction:column;gap:8px;font-size:0.88rem;">
          ${info ? `
          <div style="display:flex;justify-content:space-between;">
            <span style="color:var(--text-muted);">Modelo LLM</span>
            <span style="font-weight:600;font-size:0.82rem;">${escHtml(info.modelo_llm || '—')}</span>
          </div>
          <div style="display:flex;justify-content:space-between;">
            <span style="color:var(--text-muted);">Embeddings</span>
            <span style="font-weight:600;font-size:0.82rem;">${escHtml(info.modelo_embeddings || '—')}</span>
          </div>
          ` : '<div style="color:var(--text-muted);">No disponible</div>'}
        </div>
      </div>
      <div class="card">
        <h3 style="margin-bottom:12px;">Acciones rápidas</h3>
        <div style="display:flex;flex-direction:column;gap:8px;">
          <button class="btn btn-outline" onclick="showSection('docs', document.querySelector(\'.sidebar-item\'))">
            📁 Ir a Documentos
          </button>
          <button class="btn btn-outline" onclick="cargarSistema()">↺ Refrescar estado</button>
          <a href="${API_BASE}/docs" target="_blank" class="btn btn-outline" style="text-decoration:none;">
            📋 Ver documentación API
          </a>
        </div>
      </div>
    `;
  } catch (e) {
    container.innerHTML = `<div class="alert alert-error">Error al cargar info del sistema: ${escHtml(e.message)}</div>`;
  }
}

// ── Init ─────────────────────────────────────────────────────────────
(function init() {
  initTheme();
  // Restaurar sesión si existe (no cierra al recargar)
  const savedPin = sessionStorage.getItem('atena_admin_pin');
  if (savedPin) {
    adminPin = savedPin;
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('admin-panel').style.display = 'flex';
    cargarDocs();
  }
})();
