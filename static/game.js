// Mundo Hexagonal - Cliente Canvas y Lógica de Juego
const HEX_RADIUS = 50;
const SQRT3 = Math.sqrt(3);

class HexWorld {
  constructor() {
    this.canvas = document.getElementById("mapCanvas");
    this.ctx = this.canvas.getContext("2d");

    // Cámara (pan y zoom)
    this.camera = {
      x: 0,
      y: 0,
      zoom: 1.0,
      targetZoom: 1.0
    };

    // Estado del juego
    this.hexes = {};
    this.robot = {
      q: 0,
      r: 0,
      vida: 10,
      max_vida: 10,
      hambre: 5,
      max_hambre: 10,
      sed: 5,
      max_sed: 10,
      inventario: [],
      casa_almacen: [],
      minutos: 0,
      iteracion: 0,
      memoria_futuro: "",
      activo: true
    };

    // Posición animada del robot para traslaciones suaves
    this.robotAnim = {
      x: 0,
      y: 0,
      targetX: 0,
      targetY: 0,
      t: 1.0
    };

    this.isDragging = false;
    this.dragStart = { x: 0, y: 0 };
    this.isRunningIteration = false;
    this.autoRemainingIterations = 0;

    this.initCanvasSize();
    this.setupEventListeners();
    this.fetchInitialState();

    // Iniciar loop de render
    this.lastTime = performance.now();
    requestAnimationFrame((t) => this.renderLoop(t));
  }

  initCanvasSize() {
    const parent = this.canvas.parentElement;
    this.canvas.width = parent.clientWidth * window.devicePixelRatio;
    this.canvas.height = parent.clientHeight * window.devicePixelRatio;
    this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    this.viewWidth = parent.clientWidth;
    this.viewHeight = parent.clientHeight;
  }

  // Conversión axial (q, r) a coordenadas cartesianas (x, y) para hexágonos puntiagudos
  hexToPixel(q, r) {
    const x = HEX_RADIUS * SQRT3 * (q + r / 2);
    const y = HEX_RADIUS * (3 / 2) * r;
    return { x, y };
  }

  setupEventListeners() {
    window.addEventListener("resize", () => {
      this.initCanvasSize();
    });

    // Arrastre con ratón (Pan)
    this.canvas.addEventListener("mousedown", (e) => {
      this.isDragging = true;
      this.dragStart.x = e.clientX - this.camera.x;
      this.dragStart.y = e.clientY - this.camera.y;
    });

    window.addEventListener("mousemove", (e) => {
      if (this.isDragging) {
        this.camera.x = e.clientX - this.dragStart.x;
        this.camera.y = e.clientY - this.dragStart.y;
      }
    });

    window.addEventListener("mouseup", () => {
      this.isDragging = false;
    });

    // Zoom con rueda de ratón centrado en cursor
    this.canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
      const mouseX = e.clientX - this.canvas.getBoundingClientRect().left;
      const mouseY = e.clientY - this.canvas.getBoundingClientRect().top;

      const newZoom = Math.max(0.4, Math.min(2.5, this.camera.zoom * zoomFactor));

      this.camera.x = mouseX - (mouseX - this.camera.x) * (newZoom / this.camera.zoom);
      this.camera.y = mouseY - (mouseY - this.camera.y) * (newZoom / this.camera.zoom);
      this.camera.zoom = newZoom;
    }, { passive: false });

    // Controles táctiles básicos
    let lastTouch = null;
    this.canvas.addEventListener("touchstart", (e) => {
      if (e.touches.length === 1) {
        lastTouch = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      }
    });
    this.canvas.addEventListener("touchmove", (e) => {
      if (e.touches.length === 1 && lastTouch) {
        this.camera.x += e.touches[0].clientX - lastTouch.x;
        this.camera.y += e.touches[0].clientY - lastTouch.y;
        lastTouch = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      }
    });
    this.canvas.addEventListener("touchend", () => {
      lastTouch = null;
    });

    // Botones de Zoom y Centrar
    document.getElementById("btnZoomIn").addEventListener("click", () => {
      this.zoomFromCenter(1.2);
    });
    document.getElementById("btnZoomOut").addEventListener("click", () => {
      this.zoomFromCenter(0.8);
    });
    document.getElementById("btnCenterRobot").addEventListener("click", () => {
      this.centerOnRobot();
    });

    // Tabs laterales
    document.getElementById("tabFeedBtn").addEventListener("click", () => {
      document.getElementById("tabFeedBtn").classList.add("active");
      document.getElementById("tabMemoryBtn").classList.remove("active");
      document.getElementById("tabFeedContent").style.display = "flex";
      document.getElementById("tabMemoryContent").style.display = "none";
    });
    document.getElementById("tabMemoryBtn").addEventListener("click", () => {
      document.getElementById("tabMemoryBtn").classList.add("active");
      document.getElementById("tabFeedBtn").classList.remove("active");
      document.getElementById("tabMemoryContent").style.display = "flex";
      document.getElementById("tabFeedContent").style.display = "none";
    });

    // Botones de ejecución (10 min, 1 hora, 1 día)
    document.getElementById("btnPlay").addEventListener("click", () => {
      this.runBatchIterations(1);
    });
    document.getElementById("btnPlayHour")?.addEventListener("click", () => {
      this.runBatchIterations(6);
    });
    document.getElementById("btnPlayDay")?.addEventListener("click", () => {
      if (confirm("¿Deseas iniciar la simulación de 1 Día completo (144 iteraciones de 10 min = 24 horas)? Puedes detenerla en cualquier momento pulsando 'Detener'.")) {
        this.runBatchIterations(144);
      }
    });
    document.getElementById("btnStopAuto")?.addEventListener("click", () => {
      this.stopBatchIterations();
    });

    // Botón Reset
    document.getElementById("btnReset").addEventListener("click", () => {
      if (confirm("¿Seguro que deseas reiniciar el mundo desde cero? Se borrará el progreso actual.")) {
        this.resetGame();
      }
    });

    // Modal de Log
    document.getElementById("btnOpenLog").addEventListener("click", () => {
      this.openLogModal();
    });
    document.getElementById("btnCloseLog").addEventListener("click", () => {
      document.getElementById("logModal").classList.remove("show");
    });
    document.getElementById("btnRefreshLog").addEventListener("click", () => {
      this.loadLogContent();
    });
    document.getElementById("logModal").addEventListener("click", (e) => {
      if (e.target.id === "logModal") {
        document.getElementById("logModal").classList.remove("show");
      }
    });

    // Modal Popup de Memoria al terminar iteración
    const closeMemoryModal = () => {
      document.getElementById("memoryModal").classList.remove("show");
    };

    document.getElementById("btnCloseMemoryModal").addEventListener("click", closeMemoryModal);
    document.getElementById("btnOkMemoryModal").addEventListener("click", closeMemoryModal);
    document.getElementById("memoryModal").addEventListener("click", (e) => {
      if (e.target.id === "memoryModal") {
        closeMemoryModal();
      }
    });

    // Modal de Memorial Pionero-01
    const closeMemorialModal = () => {
      document.getElementById("memorialModal").classList.remove("show");
    };
    document.getElementById("btnMemorial")?.addEventListener("click", () => this.openMemorialModal());
    document.getElementById("btnVerMemorialTab")?.addEventListener("click", () => this.openMemorialModal());
    document.getElementById("btnCloseMemorialModal")?.addEventListener("click", closeMemorialModal);
    document.getElementById("btnOkMemorialModal")?.addEventListener("click", closeMemorialModal);
    document.getElementById("memorialModal")?.addEventListener("click", (e) => {
      if (e.target.id === "memorialModal") closeMemorialModal();
    });
  }

  async openMemorialModal() {
    try {
      const res = await fetch("/api/memorial");
      const txt = await res.text();
      document.getElementById("memorialModalText").innerText = txt;
      document.getElementById("memorialModal").classList.add("show");
    } catch (e) {
      alert("Error cargando memorial: " + e.message);
    }
  }

  zoomFromCenter(factor) {
    const cx = this.viewWidth / 2;
    const cy = this.viewHeight / 2;
    const newZoom = Math.max(0.4, Math.min(2.5, this.camera.zoom * factor));
    this.camera.x = cx - (cx - this.camera.x) * (newZoom / this.camera.zoom);
    this.camera.y = cy - (cy - this.camera.y) * (newZoom / this.camera.zoom);
    this.camera.zoom = newZoom;
  }

  centerOnRobot() {
    const pos = this.hexToPixel(this.robot.q, this.robot.r);
    this.camera.x = this.viewWidth / 2 - pos.x * this.camera.zoom;
    this.camera.y = this.viewHeight / 2 - pos.y * this.camera.zoom;
  }

  updateModelBadge(modelName) {
    const mb = document.getElementById("modelBadge");
    if (!mb || !modelName) return;
    let label = modelName;
    const lower = modelName.toLowerCase();
    if (lower.includes("gemma-3") || lower.includes("gemma 3")) label = "Gemma-3";
    else if (lower.includes("gemma")) label = "Gemma";
    else if (lower.includes("llama-3") || lower.includes("llama 3")) label = "Llama-3-8B";
    else if (lower.includes("llama")) label = "Llama";
    else if (lower.includes("qwen")) label = "Qwen";
    mb.innerText = `LM Studio (${label})`;
    mb.title = modelName;
  }

  updateAccionesDisponibles(acciones) {
    const cont = document.getElementById("accionesDisponiblesBadges");
    if (!cont) return;
    if (!acciones || acciones.length === 0) {
      cont.innerHTML = '<span class="badge" style="background: rgba(239, 68, 68, 0.2); color: #ef4444;">Sin acciones disponibles</span>';
      return;
    }
    cont.innerHTML = acciones.map(a => {
      let bg = "rgba(16, 185, 129, 0.15)";
      let color = "#34d399";
      if (a === "BEBER" || a.includes("AGUA")) {
        bg = "rgba(56, 189, 248, 0.2)";
        color = "#38bdf8";
      } else if (a === "COMER") {
        bg = "rgba(245, 158, 11, 0.2)";
        color = "#fbbf24";
      } else if (a.startsWith("ACTUALIZAR") || a.startsWith("CONSULTAR")) {
        bg = "rgba(168, 85, 247, 0.2)";
        color = "#c084fc";
      }
      return `<span class="badge" style="background: ${bg}; color: ${color}; font-weight: 500;">${a}</span>`;
    }).join("");
  }

  async fetchInitialState() {
    try {
      // Cargar versión y modelo activo
      fetch("/api/version").then(r => r.json()).then(v => {
        const b = document.getElementById("versionBadge");
        if (b && v.version) b.innerText = v.version;
      }).catch(() => {});

      fetch("/api/model").then(r => r.json()).then(m => {
        this.updateModelBadge(m.model);
      }).catch(() => {});

      const res = await fetch("/api/state");
      const data = await res.json();
      if (data.model) this.updateModelBadge(data.model);
      this.applyState(data.hexes, data.robot);
      this.centerOnRobot();
      this.updateMemoriaDisplay();
      if (data.world_summary && data.world_summary.acciones_disponibles) {
        this.updateAccionesDisponibles(data.world_summary.acciones_disponibles);
      }
    } catch (e) {
      console.error("Error cargando estado inicial:", e);
    }
  }

  applyState(hexes, robot) {
    this.hexes = hexes || this.hexes;
    if (robot) {
      const prevQ = this.robot.q;
      const prevR = this.robot.r;
      this.robot = robot;

      const targetPos = this.hexToPixel(robot.q, robot.r);
      if (prevQ !== robot.q || prevR !== robot.r) {
        this.robotAnim.targetX = targetPos.x;
        this.robotAnim.targetY = targetPos.y;
        this.robotAnim.t = 0; // Iniciar interpolación de movimiento
      } else if (this.robotAnim.t >= 1) {
        this.robotAnim.x = targetPos.x;
        this.robotAnim.y = targetPos.y;
      }

      this.updateHUD();
    }
  }

  updateHUD() {
    // Header Stats
    document.getElementById("hdrIteracion").innerText = this.robot.iteracion;
    const mins = this.robot.minutos;
    const hours = Math.floor(mins / 60);
    const remMins = mins % 60;
    document.getElementById("hdrTiempo").innerText = `${mins} min (${hours}h ${remMins}m)`;
    document.getElementById("hdrPosicion").innerText = `(${this.robot.q}, ${this.robot.r})`;

    // Robot HUD (Bars)
    const vidaPct = (this.robot.vida / this.robot.max_vida) * 100;
    document.getElementById("barVida").style.width = `${vidaPct}%`;
    document.getElementById("lblVida").innerText = `${this.robot.vida} / ${this.robot.max_vida}`;

    const hambrePct = (this.robot.hambre / this.robot.max_hambre) * 100;
    document.getElementById("barHambre").style.width = `${hambrePct}%`;
    document.getElementById("lblHambre").innerText = `${this.robot.hambre} / ${this.robot.max_hambre}`;

    const sedPct = (this.robot.sed / this.robot.max_sed) * 100;
    document.getElementById("barSed").style.width = `${sedPct}%`;
    document.getElementById("lblSed").innerText = `${this.robot.sed} / ${this.robot.max_sed}`;

    // Estado del Robot
    const dot = document.getElementById("hudStatusDot");
    if (this.robot.activo) {
      dot.innerText = "● Activo";
      dot.style.color = "#22c55e";
    } else {
      dot.innerText = "● Apagado (Game Over)";
      dot.style.color = "#ef4444";
    }

    // Mochila (3 slots)
    const slotsCont = document.getElementById("slotsInventario");
    slotsCont.innerHTML = "";
    document.getElementById("lblInventarioCount").innerText = `${this.robot.inventario.length} / 3`;
    for (let i = 0; i < 3; i++) {
      const slotDiv = document.createElement("div");
      if (i < this.robot.inventario.length) {
        const item = this.robot.inventario[i];
        slotDiv.className = `slot filled ${item}`;
        slotDiv.innerText = item.toUpperCase();
      } else {
        slotDiv.className = "slot";
        slotDiv.innerText = "Vacío";
      }
      slotsCont.appendChild(slotDiv);
    }

    // Casa Almacén (dinámico según max_casa_almacen)
    const casaCont = document.getElementById("slotsCasa");
    casaCont.innerHTML = "";
    const almacen = this.robot.casa_almacen || [];
    const maxCasa = this.robot.max_casa_almacen || 10;
    document.getElementById("lblCasaCount").innerText = `${almacen.length} / ${maxCasa}`;
    
    const itemColors = {
      madera: "#b45309",
      comida: "#15803d",
      piedra: "#64748b",
      cobre: "#d97706",
      hierro: "#94a3b8",
      diamante: "#38bdf8"
    };

    for (let i = 0; i < maxCasa; i++) {
      const slotDiv = document.createElement("div");
      slotDiv.style.width = "22px";
      slotDiv.style.height = "22px";
      slotDiv.style.borderRadius = "4px";
      slotDiv.style.border = "1px solid #2e3e55";
      slotDiv.style.background = "#111822";

      if (i < almacen.length) {
        const item = almacen[i];
        slotDiv.style.background = itemColors[item] || "#38bdf8";
        slotDiv.title = item;
      }
      casaCont.appendChild(slotDiv);
    }

    if (this.robot.memoria_futuro) {
      document.getElementById("memoryText").innerText = this.robot.memoria_futuro;
    }
  }

  async updateMemoriaDisplay() {
    try {
      const res = await fetch("/api/memoria");
      const data = await res.json();
      const elem = document.getElementById("archivoMemoriaText");
      if (elem) {
        elem.innerText = data.memoria || "(El archivo de memoria está vacío actualmente)";
      }
    } catch (e) {
      console.error("Error cargando archivo de memoria:", e);
    }
  }

  runBatchIterations(count) {
    if (this.isRunningIteration) return;
    this.autoRemainingIterations = count;
    const stopBtn = document.getElementById("btnStopAuto");
    if (stopBtn) stopBtn.style.display = count > 1 ? "inline-block" : "none";
    const hourBtn = document.getElementById("btnPlayHour");
    if (hourBtn) hourBtn.disabled = true;
    const dayBtn = document.getElementById("btnPlayDay");
    if (dayBtn) dayBtn.disabled = true;
    this.runNextIteration();
  }

  stopBatchIterations() {
    this.autoRemainingIterations = 0;
    const stopBtn = document.getElementById("btnStopAuto");
    if (stopBtn) stopBtn.style.display = "none";
    const hourBtn = document.getElementById("btnPlayHour");
    if (hourBtn) hourBtn.disabled = false;
    const dayBtn = document.getElementById("btnPlayDay");
    if (dayBtn) dayBtn.disabled = false;
    const liveStatus = document.getElementById("liveStepStatus");
    if (liveStatus) liveStatus.innerText += " (Avance automático detenido por el usuario).";
  }

  async runNextIteration() {
    if (this.isRunningIteration) return;
    if (!this.robot.activo) {
      alert("El robot está desactivado. Reinicia la partida para comenzar de nuevo.");
      return;
    }

    this.isRunningIteration = true;
    const playBtn = document.getElementById("btnPlay");
    const playIcon = document.getElementById("playIcon");
    const playSpinner = document.getElementById("playSpinner");
    const playText = document.getElementById("playText");
    const liveTag = document.getElementById("liveStepTag");
    const liveStatus = document.getElementById("liveStepStatus");
    const feedCont = document.getElementById("feedContainer");

    playBtn.disabled = true;
    playIcon.style.display = "none";
    playSpinner.style.display = "inline-block";
    playText.innerText = "IA Decidiendo...";
    liveTag.innerText = "Ejecutando...";
    liveStatus.innerText = "Conectando con el LLM en LM Studio...";
    feedCont.innerHTML = "";

    // Activar pestaña de acciones en directo
    document.getElementById("tabFeedBtn").click();

    try {
      const eventSource = new EventSource("/api/run_iteration_stream");

      eventSource.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);

          if (payload.type === "start") {
            const batchInfo = this.autoRemainingIterations > 1 ? ` [Lote: ${this.autoRemainingIterations} pendientes]` : '';
            liveStatus.innerText = `Iniciando Iteración #${payload.iteracion} (10 min)${batchInfo}...`;
          } else if (payload.type === "step") {
            this.handleStepEvent(payload);
          } else if (payload.type === "complete") {
            eventSource.close();
            this.handleCompleteEvent(payload);
          } else if (payload.type === "error") {
            eventSource.close();
            alert("Error en la ejecución: " + payload.message);
            this.finishIterationUI(false);
          }
        } catch (err) {
          console.error("Error parseando SSE:", err);
        }
      };

      eventSource.onerror = (err) => {
        console.error("Error de conexión SSE:", err);
        eventSource.close();
        this.finishIterationUI(false);
      };

    } catch (e) {
      console.error("Fallo lanzando iteración:", e);
      alert("Error iniciando la iteración: " + e.message);
      this.finishIterationUI(false);
    }
  }

  handleStepEvent(payload) {
    const step = payload.data;
    if (payload.hexes) this.hexes = payload.hexes;
    if (payload.robot) this.applyState(payload.hexes, payload.robot);

    if (step.accion === "ACTUALIZAR_MEMORIA" || step.accion === "MODIFICAR_MEMORIA" || step.accion === "CONSULTAR_MEMORIA") {
      this.updateMemoriaDisplay();
    }

    const liveStatus = document.getElementById("liveStepStatus");
    liveStatus.innerText = `Minuto ${step.minuto_global} (${step.paso_iteracion}/10): ${step.accion}`;

    const feedCont = document.getElementById("feedContainer");
    const stepDiv = document.createElement("div");
    stepDiv.className = `step-item ${step.exito ? 'success' : 'fail'}`;

    stepDiv.innerHTML = `
      <div class="step-header">
        <span class="step-badge">${step.accion}</span>
        <span class="step-time">Minuto ${step.minuto_global}</span>
      </div>
      <div class="step-msg">${step.mensaje}</div>
      ${step.comentario ? `<div class="step-thought">"${step.comentario}"</div>` : ''}
    `;

    feedCont.prepend(stepDiv);
  }

  handleCompleteEvent(payload) {
    const data = payload.data;
    if (payload.hexes) this.hexes = payload.hexes;
    if (payload.robot) this.applyState(payload.hexes, payload.robot);

    this.updateMemoriaDisplay();

    // Actualizar badges de acciones disponibles
    if (data.estado_final && data.estado_final.acciones_disponibles) {
      this.updateAccionesDisponibles(data.estado_final.acciones_disponibles);
    }

    // Si estamos en un lote automático (+1 Hora o +1 Día) y quedan iteraciones
    if (this.autoRemainingIterations > 1 && this.robot.activo) {
      this.autoRemainingIterations--;
      const liveTag = document.getElementById("liveStepTag");
      const liveStatus = document.getElementById("liveStepStatus");
      liveTag.innerText = `Iteración #${data.iteracion} finalizada`;
      liveStatus.innerText = `Completada. Quedan ${this.autoRemainingIterations} iteraciones automáticas (${this.autoRemainingIterations * 10} min). Continuando...`;

      this.finishIterationUI(true);
      setTimeout(() => {
        if (this.autoRemainingIterations > 0 && this.robot.activo) {
          this.runNextIteration();
        } else {
          this.finishIterationUI(false);
        }
      }, 700);
      return;
    }

    this.autoRemainingIterations = 0;
    const liveTag = document.getElementById("liveStepTag");
    const liveStatus = document.getElementById("liveStepStatus");
    liveTag.innerText = `Iteración #${data.iteracion} finalizada`;
    liveStatus.innerText = `Se completaron los 10 minutos. Memoria guardada.`;

    // Mostrar el popup con la memoria actualizada (solo al terminar la última o única iteración)
    const popup = document.getElementById("memoryModal");
    if (popup) {
      document.getElementById("popupTitle").innerText = `¡Iteración #${data.iteracion} Completada! (10 min)`;
      document.getElementById("popupMemoryText").innerText = data.memoria_robot || "(El archivo de memoria personal está vacío)";
      popup.classList.add("show");
    }

    this.finishIterationUI(false);
  }

  finishIterationUI(isAutoRunning = false) {
    this.isRunningIteration = false;
    const playBtn = document.getElementById("btnPlay");
    const playIcon = document.getElementById("playIcon");
    const playSpinner = document.getElementById("playSpinner");
    const playText = document.getElementById("playText");
    const playHourBtn = document.getElementById("btnPlayHour");
    const playDayBtn = document.getElementById("btnPlayDay");
    const stopAutoBtn = document.getElementById("btnStopAuto");

    if (isAutoRunning) {
      playBtn.disabled = true;
      if (playHourBtn) playHourBtn.disabled = true;
      if (playDayBtn) playDayBtn.disabled = true;
      if (stopAutoBtn) stopAutoBtn.style.display = "inline-block";
    } else {
      playBtn.disabled = false;
      playIcon.style.display = "inline-block";
      playSpinner.style.display = "none";
      playText.innerText = "+10 min";
      if (playHourBtn) playHourBtn.disabled = false;
      if (playDayBtn) playDayBtn.disabled = false;
      if (stopAutoBtn) stopAutoBtn.style.display = "none";
    }
  }

  async resetGame() {
    try {
      const res = await fetch("/api/reset", { method: "POST" });
      const data = await res.json();
      this.applyState(data.state.hexes, data.state.robot);
      this.centerOnRobot();
      document.getElementById("feedContainer").innerHTML = "";
      document.getElementById("liveStepTag").innerText = "Reiniciado";
      document.getElementById("liveStepStatus").innerText = "Mundo restablecido a la casa central.";
      this.updateMemoriaDisplay();
      if (data.state.world_summary && data.state.world_summary.acciones_disponibles) {
        this.updateAccionesDisponibles(data.state.world_summary.acciones_disponibles);
      }
    } catch (e) {
      alert("Error reiniciando: " + e.message);
    }
  }

  async openLogModal() {
    document.getElementById("logModal").classList.add("show");
    this.loadLogContent();
  }

  async loadLogContent() {
    const pre = document.getElementById("logModalText");
    pre.innerText = "Cargando log desde el servidor...";
    try {
      const res = await fetch("/api/log/text");
      const txt = await res.text();
      pre.innerText = txt || "El log está actualmente vacío.";
    } catch (e) {
      pre.innerText = "Error cargando archivo de log: " + e.message;
    }
  }

  // Bucle de renderizado continuo a 60 FPS
  renderLoop(timestamp) {
    const dt = (timestamp - this.lastTime) / 1000;
    this.lastTime = timestamp;

    this.updateAnimation(dt);
    this.draw();

    requestAnimationFrame((t) => this.renderLoop(t));
  }

  updateAnimation(dt) {
    if (this.robotAnim.t < 1.0) {
      this.robotAnim.t += dt * 3.5; // velocidad de desplazamiento suave
      if (this.robotAnim.t >= 1.0) {
        this.robotAnim.t = 1.0;
        this.robotAnim.x = this.robotAnim.targetX;
        this.robotAnim.y = this.robotAnim.targetY;
      } else {
        // Interpolación ease-out
        const ease = 1 - Math.pow(1 - this.robotAnim.t, 3);
        this.robotAnim.x = this.robotAnim.x + (this.robotAnim.targetX - this.robotAnim.x) * ease;
        this.robotAnim.y = this.robotAnim.y + (this.robotAnim.targetY - this.robotAnim.y) * ease;
      }
    }
  }

  draw() {
    const ctx = this.ctx;
    ctx.save();
    ctx.clearRect(0, 0, this.viewWidth, this.viewHeight);

    // Aplicar transformación de cámara
    ctx.translate(this.camera.x, this.camera.y);
    ctx.scale(this.camera.zoom, this.camera.zoom);

    // 1. Dibujar hexágonos conocidos y vecinos con niebla
    this.drawWorld(ctx);

    // 2. Dibujar el Robotito mono
    this.drawRobot(ctx, this.robotAnim.x, this.robotAnim.y);

    ctx.restore();
  }

  drawWorld(ctx) {
    // Primero recopilar hexágonos adyacentes a los descubiertos para dibujar la niebla exploratoria
    const fogHexes = new Set();
    const neighborOffsets = [
      { q: 1, r: 0 }, { q: -1, r: 0 },
      { q: 1, r: -1 }, { q: 0, r: -1 },
      { q: 0, r: 1 }, { q: -1, r: 1 }
    ];

    for (const key of Object.keys(this.hexes)) {
      const h = this.hexes[key];
      if (h.discovered) {
        for (const offset of neighborOffsets) {
          const nq = h.q + offset.q;
          const nr = h.r + offset.r;
          const nkey = `${nq},${nr}`;
          if (!this.hexes[nkey] || !this.hexes[nkey].discovered) {
            fogHexes.add(nkey);
          }
        }
      }
    }

    // Dibujar niebla de guerra en hexágonos vecinos desconocidos
    for (const fogKey of fogHexes) {
      const [q, r] = fogKey.split(",").map(Number);
      const pos = this.hexToPixel(q, r);
      this.drawHexagonFog(ctx, pos.x, pos.y, q, r);
    }

    // Dibujar los hexágonos descubiertos
    for (const key of Object.keys(this.hexes)) {
      const h = this.hexes[key];
      if (h.discovered) {
        const pos = this.hexToPixel(h.q, h.r);
        this.drawDiscoveredHex(ctx, pos.x, pos.y, h);
      }
    }
  }

  // Trazar el camino de un hexágono puntiagudo centrado en (x, y)
  buildHexagonPath(ctx, x, y, radius = HEX_RADIUS) {
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 180) * (60 * i + 30);
      const hx = x + radius * Math.cos(angle);
      const hy = y + radius * Math.sin(angle);
      if (i === 0) ctx.moveTo(hx, hy);
      else ctx.lineTo(hx, hy);
    }
    ctx.closePath();
  }

  // Niebla de guerra para hexágonos inexplorados
  drawHexagonFog(ctx, x, y, q, r) {
    this.buildHexagonPath(ctx, x, y, HEX_RADIUS - 1);
    ctx.fillStyle = "#111722";
    ctx.fill();

    ctx.strokeStyle = "#1e293b";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Líneas o patrón sutil de niebla
    ctx.save();
    ctx.clip();
    ctx.strokeStyle = "rgba(56, 189, 248, 0.04)";
    ctx.lineWidth = 2;
    for (let i = -HEX_RADIUS; i <= HEX_RADIUS; i += 12) {
      ctx.beginPath();
      ctx.moveTo(x + i, y - HEX_RADIUS);
      ctx.lineTo(x + i + HEX_RADIUS, y + HEX_RADIUS);
      ctx.stroke();
    }
    ctx.restore();
  }

  // Renderizado gráfico vectorial de terrenos (sin emoticonos)
  drawDiscoveredHex(ctx, x, y, hex) {
    this.buildHexagonPath(ctx, x, y, HEX_RADIUS - 1);

    // Fondo según terreno
    if (hex.terrain === "casa") {
      ctx.fillStyle = "#33261a";
      ctx.fill();
      ctx.strokeStyle = "#b45309";
      ctx.lineWidth = 2.5;
      ctx.stroke();

      this.drawHouseGraphic(ctx, x, y);
    } else if (hex.terrain === "bosque") {
      ctx.fillStyle = "#152e1f";
      ctx.fill();
      ctx.strokeStyle = "#166534";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      this.drawForestGraphic(ctx, x, y);
    } else if (hex.terrain === "pasto") {
      ctx.fillStyle = "#1e3b22";
      ctx.fill();
      ctx.strokeStyle = "#22c55e";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      this.drawPastureGraphic(ctx, x, y);
    } else if (hex.terrain === "agua") {
      ctx.fillStyle = "#0c2b45";
      ctx.fill();
      ctx.strokeStyle = "#0284c7";
      ctx.lineWidth = 2;
      ctx.stroke();

      this.drawWaterGraphic(ctx, x, y);
    } else if (hex.terrain === "montaña") {
      ctx.fillStyle = "#1e293b";
      ctx.fill();
      ctx.strokeStyle = "#64748b";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      this.drawMountainGraphic(ctx, x, y);
    } else if (hex.terrain === "en_obras") {
      ctx.fillStyle = "#2d2419";
      ctx.fill();
      ctx.strokeStyle = "#f59e0b";
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      this.drawConstructionGraphic(ctx, x, y, hex.nivel_obras || 1);
    }

    // Comprobar si el terreno está agotado temporalmente (cooldown de 60 min)
    if (hex.agotado_hasta_minuto && hex.agotado_hasta_minuto > this.robot.minutos) {
      const minsRestantes = hex.agotado_hasta_minuto - this.robot.minutos;

      // Sombreado sutil de agotamiento
      this.buildHexagonPath(ctx, x, y, HEX_RADIUS - 1);
      ctx.fillStyle = "rgba(10, 15, 26, 0.42)";
      ctx.fill();

      // Indicador badge con minutos restantes
      ctx.save();
      ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
      ctx.strokeStyle = "#f59e0b";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(x - 17, y - HEX_RADIUS + 7, 34, 13, 3);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#fbbf24";
      ctx.font = "bold 9px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(`${minsRestantes}m`, x, y - HEX_RADIUS + 17);
      ctx.restore();
    }

    // Coordenada axial en pequeñito en la parte inferior
    ctx.fillStyle = "rgba(255, 255, 255, 0.35)";
    ctx.font = "9px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`${hex.q},${hex.r}`, x, y + HEX_RADIUS - 8);
  }

  // 1. Gráfico de CASA (Acogedora cabaña con chimenea y ventana iluminada)
  drawHouseGraphic(ctx, x, y) {
    ctx.save();
    // Paredes de la casa
    ctx.fillStyle = "#78350f";
    ctx.fillRect(x - 12, y - 4, 24, 18);

    // Chimenea con humo
    ctx.fillStyle = "#451a03";
    ctx.fillRect(x + 5, y - 18, 5, 10);
    ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
    ctx.beginPath();
    ctx.arc(x + 7.5, y - 22, 2.5, 0, Math.PI * 2);
    ctx.arc(x + 10, y - 27, 3.5, 0, Math.PI * 2);
    ctx.fill();

    // Tejado triangular
    ctx.beginPath();
    ctx.moveTo(x - 16, y - 4);
    ctx.lineTo(x, y - 18);
    ctx.lineTo(x + 16, y - 4);
    ctx.closePath();
    ctx.fillStyle = "#dc2626";
    ctx.fill();
    ctx.strokeStyle = "#991b1b";
    ctx.lineWidth = 1;
    ctx.stroke();

    // Puerta cálida iluminada
    ctx.fillStyle = "#fef08a";
    ctx.fillRect(x - 4, y + 3, 8, 11);

    ctx.restore();
  }

  // 2. Gráfico de BOSQUE (Árboles de copa cónica en diferentes planos)
  drawForestGraphic(ctx, x, y) {
    ctx.save();
    // Tres árboles vectoriales
    const trees = [
      { ox: 0, oy: -6, scale: 1.0 },
      { ox: -12, oy: 6, scale: 0.8 },
      { ox: 13, oy: 8, scale: 0.85 }
    ];

    for (const tr of trees) {
      const tx = x + tr.ox;
      const ty = y + tr.oy;
      const s = tr.scale;

      // Tronco
      ctx.fillStyle = "#5c3317";
      ctx.fillRect(tx - 2 * s, ty + 2 * s, 4 * s, 8 * s);

      // Follaje (triángulos superpuestos de pino)
      ctx.fillStyle = "#14532d";
      ctx.beginPath();
      ctx.moveTo(tx - 10 * s, ty + 4 * s);
      ctx.lineTo(tx, ty - 8 * s);
      ctx.lineTo(tx + 10 * s, ty + 4 * s);
      ctx.closePath();
      ctx.fill();

      ctx.fillStyle = "#16a34a";
      ctx.beginPath();
      ctx.moveTo(tx - 8 * s, ty - 2 * s);
      ctx.lineTo(tx, ty - 14 * s);
      ctx.lineTo(tx + 8 * s, ty - 2 * s);
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();
  }

  // 3. Gráfico de PASTO (Hierba y pequeñas florecillas / animalito vectorial estilizado)
  drawPastureGraphic(ctx, x, y) {
    ctx.save();
    // Hojas de hierba
    ctx.strokeStyle = "#4ade80";
    ctx.lineWidth = 1.5;
    ctx.lineCap = "round";

    const grassTufts = [
      { ox: -12, oy: -8 },
      { ox: 14, oy: -4 },
      { ox: -6, oy: 12 },
      { ox: 10, oy: 14 }
    ];

    for (const g of grassTufts) {
      ctx.beginPath();
      ctx.moveTo(x + g.ox, y + g.oy);
      ctx.lineTo(x + g.ox - 2, y + g.oy - 6);
      ctx.moveTo(x + g.ox, y + g.oy);
      ctx.lineTo(x + g.ox + 3, y + g.oy - 7);
      ctx.stroke();
    }

    // Pequeñas florecillas silvestres
    const flowers = [
      { ox: 0, oy: -12, color: "#fef08a" },
      { ox: -14, oy: 6, color: "#f472b6" }
    ];
    for (const f of flowers) {
      ctx.fillStyle = f.color;
      ctx.beginPath();
      ctx.arc(x + f.ox, y + f.oy, 2, 0, Math.PI * 2);
      ctx.fill();
    }

    // Pequeño conejito / animalito vectorial blanco
    ctx.fillStyle = "#f8fafc";
    ctx.beginPath();
    // Cuerpo
    ctx.arc(x + 2, y + 2, 4, 0, Math.PI * 2);
    // Cabeza
    ctx.arc(x + 6, y - 1, 2.5, 0, Math.PI * 2);
    ctx.fill();
    // Orejitas
    ctx.strokeStyle = "#f8fafc";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x + 6, y - 2);
    ctx.lineTo(x + 7, y - 6);
    ctx.moveTo(x + 5, y - 2);
    ctx.lineTo(x + 5, y - 6);
    ctx.stroke();

    ctx.restore();
  }

  // 4. Gráfico de AGUA (Ondas onduladas en azul brillante)
  drawWaterGraphic(ctx, x, y) {
    ctx.save();
    ctx.strokeStyle = "rgba(56, 189, 248, 0.7)";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";

    const waves = [
      { ox: 0, oy: -10, len: 16 },
      { ox: -10, oy: 2, len: 14 },
      { ox: 8, oy: 12, len: 18 }
    ];

    for (const w of waves) {
      ctx.beginPath();
      ctx.moveTo(x + w.ox - w.len / 2, y + w.oy);
      ctx.quadraticCurveTo(x + w.ox - w.len / 4, y + w.oy - 3, x + w.ox, y + w.oy);
      ctx.quadraticCurveTo(x + w.ox + w.len / 4, y + w.oy + 3, x + w.ox + w.len / 2, y + w.oy);
      ctx.stroke();
    }
    ctx.restore();
  }

  // 5. Gráfico de MONTAÑA (Picos rocosos con facetas de sombra y cimas nevadas)
  drawMountainGraphic(ctx, x, y) {
    ctx.save();
    // Pico secundario izquierdo
    ctx.fillStyle = "#334155";
    ctx.beginPath();
    ctx.moveTo(x - 18, y + 10);
    ctx.lineTo(x - 8, y - 8);
    ctx.lineTo(x + 2, y + 10);
    ctx.closePath();
    ctx.fill();

    // Sombra pico secundario
    ctx.fillStyle = "#1e293b";
    ctx.beginPath();
    ctx.moveTo(x - 8, y - 8);
    ctx.lineTo(x + 2, y + 10);
    ctx.lineTo(x - 8, y + 10);
    ctx.closePath();
    ctx.fill();

    // Pico principal central
    ctx.fillStyle = "#475569";
    ctx.beginPath();
    ctx.moveTo(x - 10, y + 14);
    ctx.lineTo(x + 5, y - 18);
    ctx.lineTo(x + 20, y + 14);
    ctx.closePath();
    ctx.fill();

    // Sombra pico principal
    ctx.fillStyle = "#334155";
    ctx.beginPath();
    ctx.moveTo(x + 5, y - 18);
    ctx.lineTo(x + 20, y + 14);
    ctx.lineTo(x + 5, y + 14);
    ctx.closePath();
    ctx.fill();

    // Nieve en la cumbre
    ctx.fillStyle = "#f8fafc";
    ctx.beginPath();
    ctx.moveTo(x + 5, y - 18);
    ctx.lineTo(x + 10, y - 8);
    ctx.lineTo(x + 5, y - 6);
    ctx.lineTo(x, y - 8);
    ctx.closePath();
    ctx.fill();

    ctx.restore();
  }

  // 6. Gráfico de EN OBRAS (Andamios, vigas de madera y nivel de construcción)
  drawConstructionGraphic(ctx, x, y, level) {
    ctx.save();

    // Vigas / Estructura de madera
    ctx.strokeStyle = "#b45309";
    ctx.lineWidth = 2;

    // Postes verticales
    ctx.beginPath();
    ctx.moveTo(x - 10, y + 10);
    ctx.lineTo(x - 10, y - 8);
    ctx.moveTo(x + 10, y + 10);
    ctx.lineTo(x + 10, y - 8);
    // Viga superior y diagonal
    ctx.moveTo(x - 12, y - 8);
    ctx.lineTo(x + 12, y - 8);
    ctx.moveTo(x - 10, y + 8);
    ctx.lineTo(x + 10, y - 6);
    ctx.stroke();

    // Cuerda / Polea
    ctx.strokeStyle = "#f59e0b";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, y - 8);
    ctx.lineTo(x, y);
    ctx.stroke();

    // Bloque / Ladrillos
    ctx.fillStyle = "#dc2626";
    ctx.fillRect(x - 4, y, 8, 6);

    // Etiqueta de Nivel (ej: "Lvl 3/10")
    ctx.fillStyle = "rgba(0, 0, 0, 0.75)";
    ctx.beginPath();
    ctx.roundRect(x - 18, y + 8, 36, 12, 3);
    ctx.fill();
    ctx.strokeStyle = "#f59e0b";
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.fillStyle = "#fef08a";
    ctx.font = "bold 8px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`${level}/10`, x, y + 17);

    ctx.restore();
  }

  // 5. Gráfico del ROBOTITO MONO (Sin emojis, diseño vectorial puro con antena y visor)
  drawRobot(ctx, x, y) {
    ctx.save();

    // Sombra suave en el suelo
    ctx.fillStyle = "rgba(0, 0, 0, 0.4)";
    ctx.beginPath();
    ctx.ellipse(x, y + 16, 14, 5, 0, 0, Math.PI * 2);
    ctx.fill();

    // Pulso brillante de energía alrededor del robot
    const pulse = (Math.sin(performance.now() * 0.005) + 1) * 0.5;
    ctx.fillStyle = `rgba(56, 189, 248, ${0.15 + pulse * 0.15})`;
    ctx.beginPath();
    ctx.arc(x, y, 22 + pulse * 4, 0, Math.PI * 2);
    ctx.fill();

    // Orugas o base de ruedas (dos bloquecitos oscuros a los lados)
    ctx.fillStyle = "#1e293b";
    ctx.fillRect(x - 14, y + 7, 6, 8);
    ctx.fillRect(x + 8, y + 7, 6, 8);

    // Chasis / Cuerpo metálico redondeado
    ctx.fillStyle = "#cbd5e1";
    ctx.beginPath();
    ctx.roundRect(x - 12, y - 5, 24, 18, 6);
    ctx.fill();
    ctx.strokeStyle = "#475569";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Botoncitos en el pecho
    ctx.fillStyle = "#38bdf8";
    ctx.beginPath();
    ctx.arc(x - 4, y + 6, 1.8, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#22c55e";
    ctx.beginPath();
    ctx.arc(x + 4, y + 6, 1.8, 0, Math.PI * 2);
    ctx.fill();

    // Cabeza redondeada
    ctx.fillStyle = "#e2e8f0";
    ctx.beginPath();
    ctx.roundRect(x - 10, y - 17, 20, 13, 4);
    ctx.fill();
    ctx.strokeStyle = "#475569";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Visor oscuro
    ctx.fillStyle = "#0f172a";
    ctx.beginPath();
    ctx.roundRect(x - 8, y - 15, 16, 8, 3);
    ctx.fill();

    // Ojos luminosos cian (¡mono!)
    ctx.fillStyle = "#38bdf8";
    ctx.beginPath();
    ctx.arc(x - 4, y - 11, 2.2, 0, Math.PI * 2);
    ctx.arc(x + 4, y - 11, 2.2, 0, Math.PI * 2);
    ctx.fill();

    // Reflejo blanco en los ojos
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(x - 4.5, y - 11.8, 0.8, 0, Math.PI * 2);
    ctx.arc(x + 3.5, y - 11.8, 0.8, 0, Math.PI * 2);
    ctx.fill();

    // Antena con bombillita brillante
    ctx.strokeStyle = "#64748b";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, y - 17);
    ctx.lineTo(x, y - 24);
    ctx.stroke();

    ctx.fillStyle = "#f59e0b";
    ctx.beginPath();
    ctx.arc(x, y - 25, 2.5, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }
}

// Iniciar mundo cuando el DOM esté listo
window.addEventListener("DOMContentLoaded", () => {
  window.hexWorld = new HexWorld();
});
