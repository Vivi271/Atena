/* ═══════════════════════════════════════════════════════════════════
 app.js — Burbuja flotante Atena
 ═══════════════════════════════════════════════════════════════════ */

var API_BASE = window.API_BASE || '';
window.API_BASE = API_BASE;

// ── Estado ───────────────────────────────────────────────────────────
let nivelActual = localStorage.getItem('atena_nivel') || 'Principiante';
let estaGenerando = false;
let chatAbierto = false;
let quizPreguntas = [], quizIndice = 0, quizAciertos = 0, quizRespondida = false;

// ── Dark mode ────────────────────────────────────────────────────────
(function initTheme() {
 const t = localStorage.getItem('atena_theme') || 'dark';
 document.documentElement.setAttribute('data-theme', t);
})();

if (typeof window.toggleTheme !== 'function') {
 window.toggleTheme = function() {
 const cur = document.documentElement.getAttribute('data-theme');
 const next = cur === 'dark' ? 'light' : 'dark';
 document.documentElement.setAttribute('data-theme', next);
 localStorage.setItem('atena_theme', next);
 };
}

// ── Abrir/cerrar panel ───────────────────────────────────────────────
function toggleChat() {
 chatAbierto = !chatAbierto;
 const panel = document.getElementById('chat-panel');
 const btn = document.getElementById('bubble-btn');
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

// ── Restaurar historial de chat al volver a la página ────────────────
(function restaurarChat() {
  const saved = sessionStorage.getItem('atena_chat_html');
  if (!saved) return;
  const wrap = document.getElementById('panel-messages');
  const welcome = document.getElementById('panel-welcome');
  if (!wrap) return;
  if (welcome) welcome.remove();
  wrap.innerHTML = saved;
  wrap.scrollTop = wrap.scrollHeight;
})();

// ── Estado API ───────────────────────────────────────────────────────
async function checkApiStatus() {
 try {
 const r = await fetch(`${API_BASE}/salud`, { signal: AbortSignal.timeout(5000) });
 const dot = document.getElementById('status-dot');
 const txt = document.getElementById('status-text');
 if (r.ok) {
 if (dot) dot.style.background = '#8CC63F';
 if (txt) txt.textContent = 'Consultora IA activa';
 } else {
 if (dot) dot.style.background = '#f59e0b';
 if (txt) txt.textContent = 'Servicio con problemas';
 }
 } catch {
 const dot = document.getElementById('status-dot');
 const txt = document.getElementById('status-text');
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
function _eliminarTablasMd(text) {
 // Convierte tablas Markdown en listas de viñetas legibles
 const lines = text.split('\n');
 const out = [];
 let headerCells = null;

 for (let i = 0; i < lines.length; i++) {
 const l = lines[i].trim();
 // Línea separadora de tabla |---|---| → ignorar
 if (/^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$/.test(l)) {
 continue;
 }
 // Línea de tabla con pipes
 if (l.startsWith('|') && l.endsWith('|') && (l.match(/\|/g) || []).length >= 2) {
 const cells = l.slice(1, -1).split('|').map(c => c.trim()).filter(c => c);
 // Primera fila = encabezado, la saltamos pero la guardamos
 if (headerCells === null) {
 headerCells = cells;
 continue;
 }
 // Filas de datos → viñetas
 if (cells.length >= 2) {
 out.push('- **' + cells[0] + ':** ' + cells.slice(1).join(' — '));
 } else if (cells.length === 1) {
 out.push('- ' + cells[0]);
 }
 continue;
 }
 headerCells = null; // fuera de tabla
 out.push(lines[i]);
 }
 return out.join('\n');
}

function renderMd(text) {
 if (!text) return '';
 // 1. Eliminar tablas antes de renderizar
 let clean = _eliminarTablasMd(text);
 // 2. Convertir etiquetas Unity <color=...> a spans HTML
 clean = clean.replace(/<color=([^>]+)>(.*?)<\/color>/gi, '<span style="color:$1;font-size:0.85em;">$2</span>');
 try { return marked.parse(clean); }
 catch { return escHtml(clean).replace(/\n/g, '<br>'); }
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
 <div class="pmsg-avatar">${isBot ? 'A' : 'U'}</div>
 <div class="pmsg-body">
 <div class="pmsg-bubble">${isBot ? renderMd(texto) : escHtml(texto)}</div>
 ${sourcesHtml}
 <div class="pmsg-time">${ahora()}</div>
 </div>
 `;

 wrap.appendChild(div);
 wrap.scrollTop = wrap.scrollHeight;
 sessionStorage.setItem('atena_chat_html', wrap.innerHTML);
 return div;
}

function mostrarTyping() {
 ocultarBienvenida();
 const wrap = document.getElementById('panel-messages');
 const div = document.createElement('div');
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
 agregarMensaje('bot', ` ${msg}`, null);
 } else {
 const data = await r.json();
 agregarMensaje('bot', data.respuesta || '(Sin respuesta)', data.fuentes || []);
 }
 } catch(e) {
 quitarTyping();
 agregarMensaje('bot', 'No se pudo contactar al servidor. Verifica la conexión.', null);
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
let quizNivelSeleccionado = 'Principiante';

function abrirQuiz() {
 quizPreguntas = []; quizIndice = 0; quizAciertos = 0; quizRespondida = false;
 const modal = document.getElementById('quiz-modal');
 modal.classList.add('open');
 document.body.style.overflow = 'hidden';
 mostrarSelectorNivelQuiz();  // Primero elegir nivel
}

function mostrarSelectorNivelQuiz() {
 const content = document.getElementById('quiz-content');
 const niveles = [
   { key: 'Principiante', desc: 'Conceptos fundamentales de neuroanatomía' },
   { key: 'General',      desc: 'Conocimiento intermedio y aplicado' },
   { key: 'Avanzado',     desc: 'Profundización clínica y funcional' },
 ];
 const botones = niveles.map(n => `
   <button onclick="iniciarQuizConNivel('${n.key}')"
     style="width:100%;text-align:left;background:var(--bg-card);border:1px solid var(--border);
            border-radius:10px;padding:14px 18px;margin-bottom:10px;cursor:pointer;
            transition:border-color .2s,transform .1s;color:var(--text-main);"
     onmouseover="this.style.borderColor='var(--accent)';this.style.transform='translateX(3px)'"
     onmouseout="this.style.borderColor='var(--border)';this.style.transform=''">
     <strong style="display:block;margin-bottom:2px;">${n.key}</strong>
     <span style="font-size:0.82rem;color:var(--text-muted);">${n.desc}</span>
   </button>`).join('');

 content.innerHTML = `
   <div style="padding:8px 4px;">
     <p style="color:var(--text-muted);font-size:0.88rem;margin-bottom:18px;">
       Selecciona el nivel de dificultad para tu autoevaluación:
     </p>
     ${botones}
     <button onclick="iniciarQuizConNivel('todos')"
       style="width:100%;text-align:left;background:transparent;border:1px dashed var(--border);
              border-radius:10px;padding:14px 18px;cursor:pointer;color:var(--text-muted);
              transition:border-color .2s;" 
       onmouseover="this.style.borderColor='var(--accent)'"
       onmouseout="this.style.borderColor='var(--border)'">
       <strong style="display:block;color:var(--text-main);margin-bottom:2px;">Todos los niveles</strong>
       <span style="font-size:0.82rem;">Mezcla aleatoria de principiante, general y avanzado</span>
     </button>
   </div>`;
}

function iniciarQuizConNivel(nivel) {
 quizNivelSeleccionado = nivel;
 quizPreguntas = []; quizIndice = 0; quizAciertos = 0; quizRespondida = false;
 cargarPreguntasQuiz();
}

function cerrarQuiz() {
 document.getElementById('quiz-modal').classList.remove('open');
 document.body.style.overflow = '';
}

async function cargarPreguntasQuiz() {
 const content = document.getElementById('quiz-content');
 const nivelLabel = quizNivelSeleccionado === 'todos' ? 'todos los niveles' : `nivel ${quizNivelSeleccionado}`;
 content.innerHTML = `<div style="text-align:center;padding:40px;color:var(--text-muted);">
 <div class="spinner" style="border-top-color:var(--accent);margin:0 auto 16px;width:28px;height:28px;border-width:3px;"></div>
 Cargando preguntas de ${nivelLabel}…
 </div>`;

 try {
 const nivelParam = quizNivelSeleccionado && quizNivelSeleccionado !== 'todos'
   ? `&nivel=${encodeURIComponent(quizNivelSeleccionado)}` : '';
 const r = await fetch(`${API_BASE}/api/evaluacion/preguntas?cantidad=10&aleatorio=true${nivelParam}`);
 if (!r.ok) throw new Error(`HTTP ${r.status}`);
 const data = await r.json();

 if (!data.preguntas || data.preguntas.length === 0) {
 content.innerHTML = `<div style="text-align:center;padding:40px;">
 <p style="color:var(--text-muted);">No hay preguntas para este nivel. Ve al panel Admin para agregar preguntas.</p>
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
 const acerto = idx === correctaIdx;
 if (acerto) quizAciertos++;

 // Colorear opciones
 document.querySelectorAll('.quiz-option').forEach((btn, i) => {
  btn.disabled = true;
  if (i === correctaIdx) {
   btn.style.background = 'rgba(34,197,94,0.15)';
   btn.style.borderColor = '#22c55e';
   btn.style.color = '#22c55e';
  } else if (i === idx && !acerto) {
   btn.style.background = 'rgba(239,68,68,0.12)';
   btn.style.borderColor = '#ef4444';
   btn.style.color = '#ef4444';
  }
 });

 // Feedback de texto claro
 const exp = document.getElementById('quiz-explanation');
 if (acerto) {
  exp.style.cssText = 'margin-top:14px;padding:12px 16px;border-radius:10px;background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.35);color:#22c55e;font-size:0.88rem;font-weight:500;';
  exp.textContent = 'Correcto.';
 } else {
  const textoCorrecta = q.respuestas[correctaIdx]?.texto || '';
  exp.style.cssText = 'margin-top:14px;padding:12px 16px;border-radius:10px;background:rgba(239,68,68,0.10);border:1px solid rgba(239,68,68,0.35);color:#ef4444;font-size:0.88rem;';
  exp.innerHTML = `Incorrecto. La respuesta correcta es: <strong>${textoCorrecta}</strong>`;
 }
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
 const nota = ((quizAciertos/total)*5).toFixed(2);
 const pct = Math.round((quizAciertos/total)*100);
 const msg = pct >= 80 ? '¡Excelente dominio!' : pct >= 60 ? 'Buen trabajo, sigue practicando.' : 'Repasa el material e inténtalo de nuevo.';
 document.getElementById('quiz-content').innerHTML = `
 <div class="quiz-result-card">
 <div class="quiz-score">${nota}<span style="font-size:1.4rem;font-weight:400;color:var(--text-muted);">/5.0</span></div>
 <p style="color:var(--text-muted);margin:8px 0 4px;">${quizAciertos} de ${total} correctas · ${pct}%</p>
 <p style="color:var(--text-muted);font-size:0.88rem;">${msg}</p>
 </div>
 <div style="display:flex;gap:10px;margin-top:20px;">
 <button class="btn btn-outline" style="flex:1;" onclick="abrirQuiz()">Repetir</button>
 <button class="btn btn-primary" style="flex:1;" onclick="cerrarQuiz()">Cerrar</button>
 </div>
 `;
}

const qmEl = document.getElementById('quiz-modal');
if (qmEl) {
 qmEl.addEventListener('click', function(e) {
 if (e.target === this) cerrarQuiz();
 });
}

// ── Abrir automáticamente después de 2s (primera visita, excepto admin) ─────
(function autoOpen() {
 if (window.location.pathname.includes('admin')) return;
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
