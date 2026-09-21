/* ═══════════════════════════════════════════════════════════════════
   app.js — Burbuja flotante Atena
   ═══════════════════════════════════════════════════════════════════ */

const API_BASE = '';

// ── Estado ───────────────────────────────────────────────────────────
let nivelActual  = localStorage.getItem('atena_nivel') || 'Principiante';
let estaGenerando = false;
let chatAbierto  = false;
let quizPreguntas = [], quizIndice = 0, quizAciertos = 0, quizRespondida = false;

// ── Dark mode ────────────────────────────────────────────────────────
(function initTheme() {
  const t = localStorage.getItem('atena_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', t);
})();

function toggleTheme() {
  const cur  = document.documentElement.getAttribute('data-theme');
  const next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('atena_theme', next);
}

// ── Abrir/cerrar panel ───────────────────────────────────────────────
function toggleChat() {
  chatAbierto = !chatAbierto;
  const panel = document.getElementById('chat-panel');
  const btn   = document.getElementById('bubble-btn');
  const badge = document.getElementById('bubble-badge');
  const iconO = document.getElementById('icon-open');
  const iconC = document.getElementById('icon-close');
  const adminLink = document.getElementById('admin-link-wrap');

  panel.classList.toggle('open', chatAbierto);
  btn.classList.toggle('open', chatAbierto);
  iconO.style.display = chatAbierto ? 'none' : 'block';
  iconC.style.display = chatAbierto ? 'block' : 'none';
  if (badge) badge.style.display = chatAbierto ? 'none' : 'block';
  if (adminLink) adminLink.style.display = chatAbierto ? 'none' : 'block';

  if (chatAbierto) {
    setTimeout(() => {
      const input = document.getElementById('panel-input');
      if (input) input.focus();
    }, 350);
  }
}

// ── Nivel ────────────────────────────────────────────────────────────
function setNivel(btn) {
  nivelActual = btn.dataset.nivel;
  localStorage.setItem('atena_nivel', nivelActual);
  document.querySelectorAll('.nivel-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

(function initNivel() {
  document.querySelectorAll('.nivel-tab').forEach(b => {
    if (b.dataset.nivel === nivelActual) b.classList.add('active');
    else b.classList.remove('active');
  });
})();

// ── Estado API ───────────────────────────────────────────────────────
async function checkApiStatus() {
  try {
    const r = await fetch(`${API_BASE}/salud`, { signal: AbortSignal.timeout(5000) });
    const dot  = document.getElementById('status-dot');
    const txt  = document.getElementById('status-text');
    if (r.ok) {
      if (dot) dot.style.background = '#8CC63F';
      if (txt) txt.textContent = 'Consultora IA activa';
    } else {
      if (dot) dot.style.background = '#f59e0b';
      if (txt) txt.textContent = 'Servicio con problemas';
    }
  } catch {
    const dot = document.getElementById('status-dot');
    const txt  = document.getElementById('status-text');
    if (dot) dot.style.background = '#ef4444';
    if (txt) txt.textContent = 'Sin conexión';
  }
}

// ── Utilidades ───────────────────────────────────────────────────────
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 100) + 'px';
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    enviarPregunta();
  }
}

function ahora() {
  return new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
}

function ocultarBienvenida() {
  const w = document.getElementById('panel-welcome');
  if (w) w.remove();
}

// ── Renderizar mensaje ───────────────────────────────────────────────
function renderMd(text) {
  try { return marked.parse(text); }
  catch { return escHtml(text).replace(/\n/g, '<br>'); }
}

function agregarMensaje(rol, texto, fuentes) {
  ocultarBienvenida();
  const wrap = document.getElementById('panel-messages');
  const isBot = rol === 'bot';

  const div = document.createElement('div');
  div.className = `pmsg ${rol}`;

  let sourcesHtml = '';
  if (isBot && fuentes && fuentes.length > 0) {
    const items = fuentes.map(f => {
      const pag = f.pagina ? ` — pág. ${f.pagina}` : '';
      return `<div class="pmsg-source-item"><strong>${escHtml(f.fuente)}${pag}</strong></div>`;
    }).join('');
    sourcesHtml = `
      <button class="pmsg-sources" onclick="this.nextElementSibling.classList.toggle('open')">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
        ${fuentes.length} fuente${fuentes.length > 1 ? 's' : ''}
      </button>
      <div class="pmsg-sources-list">${items}</div>
    `;
  }

  div.innerHTML = `
    <div class="pmsg-avatar">${isBot ? 'A' : '👤'}</div>
    <div class="pmsg-body">
      <div class="pmsg-bubble">${isBot ? renderMd(texto) : escHtml(texto)}</div>
      ${sourcesHtml}
      <div class="pmsg-time">${ahora()}</div>
    </div>
  `;

  wrap.appendChild(div);
  wrap.scrollTop = wrap.scrollHeight;
  return div;
}

function mostrarTyping() {
  ocultarBienvenida();
  const wrap = document.getElementById('panel-messages');
  const div  = document.createElement('div');
  div.className = 'pmsg bot';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="pmsg-avatar">A</div>
    <div class="pmsg-body">
      <div class="pmsg-bubble pmsg-typing">
        <div class="dot"></div><div class="dot"></div><div class="dot"></div>
      </div>
    </div>
  `;
  wrap.appendChild(div);
  wrap.scrollTop = wrap.scrollHeight;
}

function quitarTyping() {
  const t = document.getElementById('typing-indicator');
  if (t) t.remove();
}

// ── Enviar pregunta ──────────────────────────────────────────────────
function hacerPregunta(texto) {
  const input = document.getElementById('panel-input');
  input.value = texto;
  autoResize(input);
  // Asegura que el panel esté abierto
  if (!chatAbierto) toggleChat();
  enviarPregunta();
}

async function enviarPregunta() {
  if (estaGenerando) return;
  const input = document.getElementById('panel-input');
  const pregunta = input.value.trim();
  if (!pregunta) return;

  input.value = '';
  input.style.height = '';
  estaGenerando = true;
  document.getElementById('panel-send').disabled = true;

  agregarMensaje('user', pregunta, null);
  mostrarTyping();

  try {
    const r = await fetch(`${API_BASE}/api/consultar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pregunta, nivel: nivelActual, k: 6, formato_unity: false }),
    });
    quitarTyping();
    if (!r.ok) {
      const detail = await r.json().catch(() => ({}));
      const msg = detail.detail || `Error del servidor (${r.status})`;
      agregarMensaje('bot', `⚠️ ${msg}`, null);
    } else {
      const data = await r.json();
      agregarMensaje('bot', data.respuesta || '(Sin respuesta)', data.fuentes || []);
    }
  } catch(e) {
    quitarTyping();
    agregarMensaje('bot', '⚠️ No se pudo contactar al servidor. Verifica la conexión.', null);
  } finally {
    estaGenerando = false;
    document.getElementById('panel-send').disabled = false;
    input.focus();
  }
}

function nuevaConversacion() {
  const wrap = document.getElementById('panel-messages');
  wrap.innerHTML = `
    <div class="panel-welcome" id="panel-welcome">
      <div class="panel-welcome-logo">A</div>
      <h3>Hola, soy Atena</h3>
      <p>Tu consultora especializada en neuroanatomía. Pregúntame sobre el sistema nervioso, estructuras cerebrales y más.</p>
      <div class="panel-chips">
        <button class="panel-chip" onclick="hacerPregunta(this.textContent)">¿Qué es el hipocampo?</button>
        <button class="panel-chip" onclick="hacerPregunta(this.textContent)">Lóbulos cerebrales</button>
        <button class="panel-chip" onclick="hacerPregunta(this.textContent)">Vías del dolor</button>
        <button class="panel-chip" onclick="hacerPregunta(this.textContent)">¿Qué hace el cerebelo?</button>
      </div>
    </div>
  `;
}

// ── Quiz ─────────────────────────────────────────────────────────────
function abrirQuiz() {
  quizPreguntas = []; quizIndice = 0; quizAciertos = 0; quizRespondida = false;
  const modal = document.getElementById('quiz-modal');
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
  cargarPreguntas();
}
function cerrarQuiz() {
  document.getElementById('quiz-modal').classList.remove('open');
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
        <p style="color:var(--text-muted);">No hay preguntas para el nivel <strong>${nivelActual}</strong>.</p>
        <button class="btn btn-outline" style="margin-top:16px;" onclick="cerrarQuiz()">Cerrar</button>
      </div>`;
      return;
    }
    quizPreguntas = data.preguntas;
    renderPregunta();
  } catch(e) {
    content.innerHTML = `<div style="text-align:center;padding:40px;">
      <p style="color:var(--text-muted);">No se pudo cargar el quiz.<br><small>${escHtml(e.message)}</small></p>
      <button class="btn btn-outline" style="margin-top:16px;" onclick="cerrarQuiz()">Cerrar</button>
    </div>`;
  }
}

function renderPregunta() {
  const q = quizPreguntas[quizIndice];
  const total = quizPreguntas.length;
  document.getElementById('quiz-content').innerHTML = `
    <div class="quiz-progress"><div class="quiz-progress-fill" style="width:${(quizIndice/total)*100}%"></div></div>
    <div class="quiz-question">
      <div class="quiz-question-num">Pregunta ${quizIndice+1} de ${total} · ${escHtml(nivelActual)}${q.tema ? ' · ' + escHtml(q.tema) : ''}</div>
      <div class="quiz-question-text">${escHtml(q.enunciado)}</div>
      <div class="quiz-options" id="quiz-options">
        ${q.respuestas.map((r,i) => `
          <button class="quiz-option" id="opt-${i}" onclick="responder(${i})" data-correcta="${r.es_correcta}">
            ${escHtml(r.texto)}
          </button>`).join('')}
      </div>
      <div id="quiz-explanation"></div>
    </div>
    <div id="quiz-nav" style="display:none;">
      <button class="btn btn-primary" onclick="siguientePregunta()" style="margin-top:12px;width:100%;">
        ${quizIndice+1 < total ? 'Siguiente →' : 'Ver resultados'}
      </button>
    </div>
  `;
}

function responder(idx) {
  if (quizRespondida) return;
  quizRespondida = true;
  const q = quizPreguntas[quizIndice];
  const correctaIdx = q.respuestas.findIndex(r => r.es_correcta);
  if (idx === correctaIdx) quizAciertos++;
  document.querySelectorAll('.quiz-option').forEach((btn, i) => {
    btn.disabled = true;
    if (i === correctaIdx) btn.classList.add('correct');
    else if (i === idx) btn.classList.add('wrong');
  });
  document.getElementById('quiz-nav').style.display = 'block';
}

function siguientePregunta() {
  quizRespondida = false;
  quizIndice++;
  if (quizIndice < quizPreguntas.length) renderPregunta();
  else mostrarResultados();
}

function mostrarResultados() {
  const total = quizPreguntas.length;
  const nota  = ((quizAciertos/total)*5).toFixed(2);
  const pct   = Math.round((quizAciertos/total)*100);
  const emoji = pct >= 80 ? '🎉' : pct >= 60 ? '👍' : '📖';
  const msg   = pct >= 80 ? '¡Excelente dominio!' : pct >= 60 ? 'Buen trabajo, sigue practicando.' : 'Repasa el material e inténtalo de nuevo.';
  document.getElementById('quiz-content').innerHTML = `
    <div class="quiz-result-card">
      <div style="font-size:2.5rem;">${emoji}</div>
      <div class="quiz-score">${nota}<span style="font-size:1.4rem;font-weight:400;color:var(--text-muted);">/5.0</span></div>
      <p style="color:var(--text-muted);margin:8px 0 4px;">${quizAciertos} de ${total} correctas · ${pct}% aciertos</p>
      <p style="color:var(--text-muted);font-size:0.88rem;">${msg}</p>
    </div>
    <div style="display:flex;gap:10px;margin-top:20px;">
      <button class="btn btn-outline" style="flex:1;" onclick="abrirQuiz()">🔄 Repetir</button>
      <button class="btn btn-primary" style="flex:1;" onclick="cerrarQuiz()">Cerrar</button>
    </div>
  `;
}

document.getElementById('quiz-modal').addEventListener('click', function(e) {
  if (e.target === this) cerrarQuiz();
});

// ── Abrir automáticamente después de 2s (primera visita) ─────────────
(function autoOpen() {
  const visited = sessionStorage.getItem('atena_visited');
  if (!visited) {
    setTimeout(() => {
      if (!chatAbierto) toggleChat();
      sessionStorage.setItem('atena_visited', '1');
    }, 1800);
  }
})();

// ── Init ─────────────────────────────────────────────────────────────
checkApiStatus();
setInterval(checkApiStatus, 120000);
