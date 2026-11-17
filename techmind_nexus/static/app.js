// app.js - Interfaz web de TECHMIND Nexus

const $mensajes = document.getElementById("mensajes");
const $opciones = document.getElementById("opciones");
const $entrada = document.getElementById("entrada");
const $alertas = document.getElementById("alertas");

// ---------- mensajes ----------
function agregarMensaje(texto, quien, meta = "") {
  const div = document.createElement("div");
  div.className = `msg ${quien}`;
  const burbuja = document.createElement("div");
  burbuja.className = "burbuja";
  burbuja.textContent = texto;          // textContent: evita inyección de HTML
  div.appendChild(burbuja);
  if (meta) {
    const m = document.createElement("div");
    m.className = "meta";
    m.innerHTML = meta;
    div.appendChild(m);
  }
  $mensajes.appendChild(div);
  $mensajes.scrollTop = $mensajes.scrollHeight;
  return div;
}

function mostrarEscribiendo() {
  const div = document.createElement("div");
  div.className = "msg bot escribiendo";
  div.innerHTML = '<div class="burbuja"><span></span><span></span><span></span></div>';
  $mensajes.appendChild(div);
  $mensajes.scrollTop = $mensajes.scrollHeight;
  return div;
}

function mostrarOpciones(opciones, sugerencias) {
  $opciones.innerHTML = "";
  opciones.forEach((op) => {
    const b = document.createElement("button");
    b.textContent = op;
    b.onclick = () => enviar(op);
    $opciones.appendChild(b);
  });
  sugerencias.forEach((s) => {
    const b = document.createElement("button");
    b.className = "sugerencia";
    b.textContent = s.texto;
    b.onclick = () => enviar(s.mensaje);
    $opciones.appendChild(b);
  });
  $mensajes.scrollTop = $mensajes.scrollHeight; // que no tape el último mensaje
}

const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function enviar(texto) {
  texto = texto.trim();
  if (!texto) return;
  agregarMensaje(texto, "usuario");
  $opciones.innerHTML = "";
  $entrada.value = "";
  const cargando = mostrarEscribiendo();
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensaje: texto }),
    });
    const datos = await r.json();
    cargando.remove();
    let meta = "";
    if (datos.intencion && !datos.intencion.startsWith("/")) {
      meta = `${esc(datos.titulo)} · <span class="conf">confianza ${Math.round(datos.confianza * 100)}%</span>`;
    }
    agregarMensaje(datos.respuesta, "bot", meta);
    mostrarOpciones(datos.opciones || [], datos.sugerencias || []);
  } catch (e) {
    cargando.remove();
    agregarMensaje("⚠️ No me pude conectar con el servidor. ¿Está corriendo app.py?", "bot");
  }
  $entrada.focus();
}

document.getElementById("form-chat").addEventListener("submit", (e) => {
  e.preventDefault();
  enviar($entrada.value);
});

document.querySelectorAll("#chips button").forEach((b) =>
  b.addEventListener("click", () => enviar(b.dataset.msg))
);

// ---------- estado del hardware ----------
function pintarPildora(id, estado) {
  const el = document.getElementById(id);
  el.classList.remove("on", "sim", "off");
  el.classList.add(estado === "conectado" ? "on" : estado === "simulado" ? "sim" : "off");
  el.title = estado;
}

function dibujarGrafico(lecturas) {
  const c = document.getElementById("grafico");
  const ctx = c.getContext("2d");
  const W = (c.width = c.clientWidth * devicePixelRatio);
  const H = (c.height = 90 * devicePixelRatio);
  ctx.clearRect(0, 0, W, H);
  if (lecturas.length < 2) {
    ctx.fillStyle = "#8b94b3";
    ctx.font = `${12 * devicePixelRatio}px system-ui`;
    ctx.fillText("Juntando lecturas (1 cada 30 s)…", 8, H / 2);
    return;
  }
  const linea = (valores, min, max, color) => {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2 * devicePixelRatio;
    valores.forEach((v, i) => {
      const x = (i / (valores.length - 1)) * W;
      const y = H - ((v - min) / (max - min || 1)) * (H - 10) - 5;
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    });
    ctx.stroke();
  };
  const t = lecturas.map((l) => l.temperatura);
  const h = lecturas.map((l) => l.humedad);
  linea(t, Math.min(...t) - 1, Math.max(...t) + 1, "#fb923c");
  linea(h, Math.min(...h) - 2, Math.max(...h) + 2, "#38bdf8");
}

async function actualizarEstado() {
  try {
    const e = await (await fetch("/api/estado")).json();
    pintarPildora("p-uno", e.uno);
    pintarPildora("p-esp", e.esp32);
    document.getElementById("p-temp").textContent = `🌡️ ${e.temperatura ?? "--"} °C`;
    document.getElementById("p-hum").textContent = `💧 ${e.humedad ?? "--"} %`;
    $alertas.innerHTML = (e.alertas || []).map((a) => `<div class="alerta">${esc(a)}</div>`).join("");
    dibujarGrafico(e.lecturas || []);
  } catch (_) {
    pintarPildora("p-uno", "off");
    pintarPildora("p-esp", "off");
  }
}

// ---------- enseñar ----------
document.getElementById("form-ensenar").addEventListener("submit", async (e) => {
  e.preventDefault();
  const estado = document.getElementById("ensenar-estado");
  const form = new FormData(e.target);
  estado.className = "estado-form";
  estado.textContent = "Entrenando modelo…";
  const r = await fetch("/api/ensenar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(Object.fromEntries(form)),
  });
  const datos = await r.json();
  if (datos.ok) {
    estado.className = "estado-form ok";
    estado.textContent = `✅ Aprendí el tema "${datos.tag}". ¡Probalo en el chat!`;
    e.target.reset();
  } else {
    estado.className = "estado-form error";
    estado.textContent = `❌ ${datos.error}`;
  }
});

// ---------- inicio ----------
agregarMensaje(
  "¡Hola! Soy TECHMIND Nexus 🤖\nContame qué problema tenés con tu PC, red o software y te ayudo a resolverlo.\n\nTip: escribí /ayuda para ver todo lo que sé hacer.",
  "bot"
);
actualizarEstado();
setInterval(actualizarEstado, 3000);
$entrada.focus();
