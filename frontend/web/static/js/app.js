/* ═══════════════════════════════════════════════════════════════════
   app.js — Chat RAG + Dark Mode + Quiz
   Llama a los endpoints existentes de FastAPI.
   ═══════════════════════════════════════════════════════════════════ */

// ── Config ───────────────────────────────────────────────────────────
// En producción la API y el frontend son el mismo servidor → URL relativa.
// En desarrollo local con el backend en otro puerto, ajusta API_BASE.
const API_BASE = '';  // Vacío = mismo origen (producción y local con el backend sirviendo el frontend)

// ── Estado global ────────────────────────────────────────────────────
let nivelActual = localStorage.getItem('atena_nivel') || 'Principiante';
let historialLocal = JSON.parse(localStorage.getItem('atena_historial') || '[]');
let conversacionActual = [];
let estaGenerando = false;

// Quiz state
let quizPreguntas = [];
let quizIndice = 0;
let quizAciertos = 0;
let quizRespondida = false;

// ── Dark mode (persiste en localStorage) ─────────────────────────────
function initTheme() {
  const saved = localStorage.getItem('atena_theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('atena_theme', next);
}

// ── Nivel ────────────────────────────────────────────────────────────
function setNivel(btn) {
  nivelActual = btn.dataset.nivel;
  localStorage.setItem('atena_nivel', nivelActual);
  document.querySelectorAll('.nivel-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const disp = document.getElementById('nivel-display');
  if (disp) disp.textContent = nivelActual;
}

function initNivel() {
  document.querySelectorAll('.nivel-btn').forEach(b => {
    if (b.dataset.nivel === nivelActual) b.classList.add('active');
    else b.classList.remove('active');
  });
  const disp = document.getElementById('nivel-display');
  if (disp) disp.textContent = nivelActual;
}

// ── Sidebar mobile ───────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ── Estado del API ───────────────────────────────────────────────────
async function checkApiStatus() {
  try {
    const r = await fetch(`${API_BASE}/salud`, { signal: AbortSignal.timeout(5000) });
    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-text');
    if (r.ok) {
      dot.style.background = '#22c55e';
      txt.textContent = 'API activa';
    } else {
      dot.style.background = '#f59e0b';
      txt.textContent = 'API con problemas';
    }
  } catch {
    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-text');
    dot.style.background = '#ef4444';
    txt.textContent = 'Sin conexión';
  }
}

// ── Chat ─────────────────────────────────────────────────────────────
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

function handleInputKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    enviarPregunta();
  }
}

function hacerPregunta(texto) {
  const input = document.getElementById('chat-input');
  input.value = texto;
  autoResize(input);
  enviarPregunta();
}

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function renderMd(text) {
  try { return marked.parse(text); }
  catch { return escapeHtml(text).replace(/\n/g,'<br>'); }
}

function ocultarBienvenida() {
  const w = document.getElementById('welcome-screen');
  if (w) w.remove();
}

function agregarMensaje(rol, texto, fuentes) {
  ocultarBienvenida();
  const wrap = document.getElementById('chat-messages');
  const isBot = rol === 'bot';

  const div = document.createElement('div');
  div.className = `msg ${rol}`;
  div.innerHTML = `
    <div class="msg-avatar">${isBot ? 'A' : '👤'}</div>
    <div class="msg-body">
      <div class="msg-bubble">${isBot ? renderMd(texto) : escapeHtml(texto)}</div>
      ${isBot && fuentes && fuentes.length ? renderFuentes(fuentes) : ''}
    </div>
  `;
  wrap.appendChild(div);
  div.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return div;
}

function renderFuentes(fuentes) {
  const items = fuentes.map(f => {
    const pag = f.pagina ? ` — pág. ${f.pagina}` : '';
    const frag = f.fragmento ? `<br><span style="font-size:0.77rem;opacity:0.8;">"${escapeHtml(f.fragmento.substring(0,120))}…"</span>` : '';
    return `<div class="source-item"><strong>${escapeHtml(f.fuente)}${pag}</strong>${frag}</div>`;
  }).join('');

  return `
    <button class="sources-toggle" onclick="this.nextElementSibling.classList.toggle('open'); this.querySelector('.src-arrow').style.transform = this.nextElementSibling.classList.contains('open') ? 'rotate(90deg)' : ''">
      <svg class="src-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="transition:transform 0.2s"><polyline points="9 18 15 12 9 6"/></svg>
      Ver ${fuentes.length} fuente${fuentes.length > 1 ? 's' : ''}
    </button>
    <div class="sources-list">${items}</div>
  `;
}

function mostrarTyping() {
  ocultarBienvenida();
  const wrap = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'msg bot';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="msg-avatar">A</div>
    <div class="msg-body">
      <div class="msg-bubble typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  wrap.appendChild(div);
  div.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return div;
}

function quitarTyping() {
  const t = document.getElementById('typing-indicator');
  if (t) t.remove();
}

async function enviarPregunta() {
  if (estaGenerando) return;

  const input = document.getElementById('chat-input');
  const pregunta = input.value.trim();
  if (!pregunta) return;

  // Limpiar input
  input.value = '';
  input.style.height = '';

  // Bloquear envío
  estaGenerando = true;
  const sendBtn = document.getElementById('send-btn');
  sendBtn.disabled = true;

  // Mostrar mensaje del usuario
  agregarMensaje('user', pregunta, null);

  // Guardar en conversación actual
  conversacionActual.push({ rol: 'user', texto: pregunta });

  // Mostrar typing
  mostrarTyping();

  try {
    const resp = await fetch(`${API_BASE}/api/consultar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pregunta,
        nivel: nivelActual,
        k: 6,
        formato_unity: false,
      }),
    });

    quitarTyping();

    if (!resp.ok) {
      const err = await resp.text();
      agregarMensaje('bot', `⚠️ Error del servidor (${resp.status}). Intenta de nuevo.`, null);
      console.error('[Atena] Error API:', err);
    } else {
      const data = await resp.json();
      const respuesta = data.respuesta || '(Sin respuesta del servidor)';
      const fuentes = data.fuentes || [];
      agregarMensaje('bot', respuesta, fuentes);
      conversacionActual.push({ rol: 'bot', texto: respuesta });

      // Guardar historial
      guardarEnHistorial(pregunta, respuesta);
    }
  } catch (e) {
    quitarTyping();
    agregarMensaje('bot', '⚠️ No se pudo contactar al servidor. Verifica tu conexión.', null);
    console.error('[Atena] Fetch error:', e);
  } finally {
    estaGenerando = false;
    sendBtn.disabled = false;
    input.focus();
  }
}

// ── Historial local ──────────────────────────────────────────────────
function guardarEnHistorial(pregunta, respuesta) {
  const item = {
    id: Date.now(),
    titulo: pregunta.substring(0, 55) + (pregunta.length > 55 ? '…' : ''),
    fecha: new Date().toISOString(),
  };
  historialLocal.unshift(item);
  if (historialLocal.length > 50) historialLocal = historialLocal.slice(0, 50);
  localStorage.setItem('atena_historial', JSON.stringify(historialLocal));
  renderHistorial();
}

function renderHistorial() {
  const lista = document.getElementById('historial-lista');
  if (!lista) return;
  if (historialLocal.length === 0) {
    lista.innerHTML = '<div style="padding:8px 12px;font-size:0.8rem;color:var(--text-muted);">Sin conversaciones aún</div>';
    return;
  }
  lista.innerHTML = historialLocal.slice(0, 15).map(h => `
    <button class="sidebar-item" title="${escapeHtml(h.titulo)}">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      ${escapeHtml(h.titulo)}
    </button>
  `).join('');
}

function nuevaConversacion() {
  conversacionActual = [];
  const wrap = document.getElementById('chat-messages');
  wrap.innerHTML = `
    <div class="welcome-screen" id="welcome-screen">
      <div class="welcome-logo" translate="no">Atena</div>
      <p class="welcome-sub">Tu consultor especializado en neuroanatomía. Hazme cualquier pregunta sobre el sistema nervioso, estructuras cerebrales o temas del laboratorio.</p>
      <div class="welcome-chips">
        <button class="chip" onclick="hacerPregunta(this.textContent)">¿Qué es el hipocampo?</button>
        <button class="chip" onclick="hacerPregunta(this.textContent)">Explica las vías del dolor</button>
        <button class="chip" onclick="hacerPregunta(this.textContent)">¿Cuáles son los lóbulos cerebrales?</button>
        <button class="chip" onclick="hacerPregunta(this.textContent)">Diferencias entre SNC y SNP</button>
        <button class="chip" onclick="hacerPregunta(this.textContent)">¿Qué hace el cerebelo?</button>
      </div>
    </div>
  `;
}

// ── Quiz ─────────────────────────────────────────────────────────────
function abrirQuiz() {
  quizPreguntas = [];
  quizIndice = 0;
  quizAciertos = 0;
  quizRespondida = false;

  const modal = document.getElementById('quiz-modal');
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';

  cargarPreguntas();
}

function cerrarQuiz() {
  const modal = document.getElementById('quiz-modal');
  modal.classList.remove('open');
  document.body.style.overflow = '';
}

async function cargarPreguntas() {
  const content = document.getElementById('quiz-content');
  content.innerHTML = `<div style="text-align:center;padding:40px;color:var(--text-muted);">
    <div class="spinner" style="border-top-color:var(--accent);margin:0 auto 16px;width:28px;height:28px;border-width:3px;"></div>
    Cargando preguntas de nivel ${nivelActual}…
  </div>`;

  try {
    const r = await fetch(`${API_BASE}/api/evaluacion/preguntas?nivel=${encodeURIComponent(nivelActual)}&cantidad=10&aleatorio=true`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();

    if (!data.preguntas || data.preguntas.length === 0) {
      content.innerHTML = `<div style="text-align:center;padding:40px;">
        <p style="color:var(--text-muted);">No hay preguntas disponibles para el nivel <strong>${nivelActual}</strong>.</p>
        <button class="btn btn-outline" style="margin-top:16px;" onclick="cerrarQuiz()">Cerrar</button>
      </div>`;
      return;
    }

    quizPreguntas = data.preguntas;
    quizIndice = 0;
    quizAciertos = 0;
    renderPregunta();
  } catch (e) {
    content.innerHTML = `<div style="text-align:center;padding:40px;">
      <p style="color:var(--text-muted);">No se pudo cargar el quiz. Verifica la conexión.</p>
      <button class="btn btn-outline" style="margin-top:16px;" onclick="cerrarQuiz()">Cerrar</button>
    </div>`;
    console.error('[Quiz] Error:', e);
  }
}

function renderPregunta() {
  const content = document.getElementById('quiz-content');
  const q = quizPreguntas[quizIndice];
  const total = quizPreguntas.length;
  const progPct = (quizIndice / total) * 100;

  const opciones = q.respuestas.map((r, i) => `
    <button class="quiz-option" id="opt-${i}" onclick="responder(${i})" data-id="${r.id}" data-correcta="${r.es_correcta}">
      ${escapeHtml(r.texto)}
    </button>
  `).join('');

  content.innerHTML = `
    <div class="quiz-progress"><div class="quiz-progress-fill" style="width:${progPct}%"></div></div>
    <div class="quiz-question">
      <div class="quiz-question-num">Pregunta ${quizIndice + 1} de ${total} · ${escapeHtml(nivelActual)} · ${escapeHtml(q.tema || '')}</div>
      <div class="quiz-question-text">${escapeHtml(q.enunciado)}</div>
      <div class="quiz-options" id="quiz-options">${opciones}</div>
      <div id="quiz-explanation" style="display:none;"></div>
    </div>
    <div id="quiz-nav" style="display:none;">
      <button class="btn btn-primary" onclick="siguientePregunta()" style="margin-top:12px;width:100%;">
        ${quizIndice + 1 < total ? 'Siguiente pregunta →' : 'Ver resultados'}
      </button>
    </div>
  `;
}

function responder(idx) {
  if (quizRespondida) return;
  quizRespondida = true;

  const q = quizPreguntas[quizIndice];
  const opciones = document.querySelectorAll('.quiz-option');
  const correctaIdx = q.respuestas.findIndex(r => r.es_correcta);
  const esCorrecta = idx === correctaIdx;

  if (esCorrecta) quizAciertos++;

  opciones.forEach((btn, i) => {
    btn.disabled = true;
    if (i === correctaIdx) btn.classList.add('correct');
    else if (i === idx && !esCorrecta) btn.classList.add('wrong');
  });

  // Registrar en la API (sin bloquear)
  const respuestaTexto = q.respuestas[idx]?.texto || '';
  const correctaTexto = q.respuestas[correctaIdx]?.texto || '';
  const pin = sessionStorage.getItem('atena_admin_pin') || '';
  if (pin) {
    fetch(`${API_BASE}/api/admin/evaluacion/registrar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Pin': pin },
      body: JSON.stringify({
        pregunta: q.enunciado,
        respuesta_usuario: respuestaTexto,
        respuesta_correcta: correctaTexto,
        es_correcta: esCorrecta,
        explicacion: '',
      }),
    }).catch(() => {}); // No bloqueante
  }

  // Mostrar siguiente
  document.getElementById('quiz-nav').style.display = 'block';
  quizRespondida = false; // reset para la función guardar ya ocurrió
  quizRespondida = true;
}

function siguientePregunta() {
  quizRespondida = false;
  quizIndice++;
  if (quizIndice < quizPreguntas.length) {
    renderPregunta();
  } else {
    mostrarResultados();
  }
}

function mostrarResultados() {
  const total = quizPreguntas.length;
  const nota = ((quizAciertos / total) * 5).toFixed(2);
  const pct = Math.round((quizAciertos / total) * 100);

  let emoji = pct >= 80 ? '🎉' : pct >= 60 ? '👍' : '📖';
  let msg   = pct >= 80 ? '¡Excelente dominio del tema!' : pct >= 60 ? 'Buen trabajo, sigue practicando.' : 'Repasa el material y vuelve a intentarlo.';

  document.getElementById('quiz-content').innerHTML = `
    <div class="quiz-result-card">
      <div style="font-size:2.5rem;">${emoji}</div>
      <div class="quiz-score">${nota}<span style="font-size:1.4rem;font-weight:400;color:var(--text-muted);">/5.0</span></div>
      <p style="color:var(--text-muted);margin:8px 0 4px;">${quizAciertos} de ${total} correctas · ${pct}% aciertos</p>
      <p style="color:var(--text-muted);font-size:0.88rem;">${msg}</p>
    </div>
    <div style="display:flex;gap:10px;margin-top:20px;">
      <button class="btn btn-outline" style="flex:1;" onclick="abrirQuiz()">🔄 Repetir quiz</button>
      <button class="btn btn-primary" style="flex:1;" onclick="cerrarQuiz()">Cerrar</button>
    </div>
  `;
}

// ── Cerrar modal al click fuera ──────────────────────────────────────
document.getElementById('quiz-modal').addEventListener('click', function(e) {
  if (e.target === this) cerrarQuiz();
});

// ── Inicialización ───────────────────────────────────────────────────
(function init() {
  initTheme();
  initNivel();
  renderHistorial();
  checkApiStatus();
  // Verificar estado API cada 2 minutos
  setInterval(checkApiStatus, 120000);
  // Focus en el input
  const input = document.getElementById('chat-input');
  if (input) input.focus();
  // Burger solo en mobile
  const mediaQuery = window.matchMedia('(max-width:768px)');
  const burger = document.getElementById('burger');
  const handleMedia = (mq) => { if (burger) burger.style.display = mq.matches ? 'block' : 'none'; };
  handleMedia(mediaQuery);
  mediaQuery.addEventListener('change', handleMedia);
})();
