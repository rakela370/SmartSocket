"use strict";
// UI sends commands. Only the Python controller decides whether power is on.
const el = id => document.getElementById(id);
let latest = null;
let sliderBusy = false;
let pendingCommands = 0;
let commandTail = Promise.resolve();
let changeTimer = null;
const errorText = "Greška, tražite više od dozvoljene energije za isporuku.";

// Queue commands in the order of user clicks; never silently discard START.
function api(path, value = null) {
  const send = async () => {
    pendingCommands++;
    try {
      const response = await fetch("/api/" + path, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Socket-UI": "1" },
        body: JSON.stringify(value === null ? {} : { value })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Komanda nije prihvaćena.");
      render(result);
    } catch (err) {
      el("alert").textContent = err.message;
      el("alert").classList.add("error");
      el("load-note").textContent = err.message;
      el("load-note").classList.add("error");
    } finally {
      pendingCommands--;
    }
  };
  commandTail = commandTail.then(send, send);
  return commandTail;
}

function render(s) {
  latest = s;
  const running = s.state === "RUNNING";
  const tripped = s.state === "TRIPPED";
  const finished = s.state === "FINISHED";
  el("top-status").textContent = ({IDLE:"SPREMNA",RUNNING:"AKTIVNA",TRIPPED:"GREŠKA",FINISHED:"ZAVRŠENO"})[s.state];
  el("state-name").textContent = s.state;
  el("relay-text").textContent = "KONTAKTOR: " + (s.output_enabled ? "UKLJUČEN" : "ISKLJUČEN");
  el("power-dot").className = "status-dot" + (running ? "" : " gray");
  el("error-lamp").classList.toggle("on", s.error_led_on);
  el("device-display").innerHTML = tripped ? "GREŠKA" : s.limit_w + " <span>W</span>";
  el("device-message").textContent = tripped ? errorText : running ? "IZLAZ AKTIVAN · MJERENJE" : finished ? "VRIJEME ISTEKLO" : "SPREMNO · IZLAZ ISKLJUČEN";
  el("device-display").parentElement.classList.toggle("is-error", tripped);
  el("remaining").textContent = formatTime(s.remaining_s);
  el("measured").textContent = s.measured_power_w === null ? "— W" : s.measured_power_w.toFixed(0) + " W";
  el("delivered").textContent = s.delivered_power_w.toFixed(0) + " W";
  el("energy").textContent = s.energy_wh.toFixed(3) + " Wh";
  el("load-limit").textContent = s.limit_w + " W";
  el("current").textContent = s.current_a.toFixed(2) + " A";
  el("load-status").textContent = running ? "POTROŠAČ DOBIJA NAPAJANJE" : "POTROŠAČ NIJE NAPAJAN";
  el("load-lamp").classList.toggle("on", running);
  el("load-status-dot").className = "status-dot" + (running ? "" : " gray");
  el("load-display").innerHTML = s.requested_power_w.toFixed(0) + "<span> W</span>";
  if (!sliderBusy) {
    el("load-slider").value = s.requested_power_w;
    el("requested").textContent = s.requested_power_w.toFixed(0);
  }
  for (const btn of document.querySelectorAll(".power-choice")) {
    btn.classList.toggle("selected", Number(btn.dataset.limit) === s.limit_w);
    btn.disabled = running || tripped;
  }
  el("duration").disabled = running || tripped;
  el("duration-set").disabled = running || tripped;
  if (document.activeElement !== el("duration")) el("duration").value = s.duration_s;
  el("start-btn").disabled = running || tripped || finished;
  el("stop-btn").disabled = !running;
  el("reset-btn").disabled = running;

  const message = tripped ? s.message : finished ? "Isteklo podešeno vrijeme. Izlaz je isključen. Pritisni RESET za novu sesiju." : running ? "Utičnica radi. Kontroler neprekidno prati izmjerenu snagu." : "Izaberi limit i vrijeme, pa pritisni UKLJUČI.";
  el("alert").textContent = message;
  el("alert").classList.toggle("error", tripped);
  el("load-note").textContent = tripped ? "Zaštita je isključila izlaz: " + s.message : running ? "Uređaj dobija " + s.delivered_power_w.toFixed(0) + " W. Ako zahtjev premaši limit, izlaz se isključuje." : "Podešeni zahtjev će se provjeriti tek po uključivanju utičnice.";
  el("load-note").classList.toggle("error", tripped);
}
function formatTime(value) {
  const seconds = Math.max(0, Math.ceil(value));
  return String(Math.floor(seconds / 60)).padStart(2, "0") + ":" + String(seconds % 60).padStart(2, "0");
}
async function refresh() {
  if (pendingCommands > 0) return;
  try {
    const r = await fetch("/api/state", { cache: "no-store" });
    if (!r.ok) throw new Error("Kontroler nije dostupan");
    render(await r.json());
  } catch (_err) {
    el("top-status").textContent = "VEZA PREKINUTA";
    el("alert").textContent = "Izgubljena lokalna veza sa simulatorom. Stanje izlaza nije poznato.";
    el("alert").classList.add("error");
  }
}
function showTab(name) {
  const socket = name === "socket";
  el("panel-socket").hidden = !socket;
  el("panel-load").hidden = socket;
  for (const [id, active] of [["tab-socket", socket], ["tab-load", !socket]]) {
    el(id).classList.toggle("active", active);
    el(id).setAttribute("aria-selected", String(active));
  }
}
el("tab-socket").addEventListener("click", () => showTab("socket"));
el("tab-load").addEventListener("click", () => showTab("load"));
for (const button of document.querySelectorAll(".power-choice")) {
  button.addEventListener("click", () => api("limit", Number(button.dataset.limit)));
}
el("duration-set").addEventListener("click", () => api("duration", Number(el("duration").value)));
el("start-btn").addEventListener("click", () => api("start"));
el("stop-btn").addEventListener("click", () => api("stop"));
el("reset-btn").addEventListener("click", () => api("reset"));
el("load-slider").addEventListener("input", () => {
  sliderBusy = true;
  el("requested").textContent = el("load-slider").value;
  el("load-display").innerHTML = el("load-slider").value + "<span> W</span>";
  clearTimeout(changeTimer);
  changeTimer = setTimeout(() => {
    sliderBusy = false;
    api("load", Number(el("load-slider").value));
  }, 130);
});
el("load-slider").addEventListener("change", () => {
  clearTimeout(changeTimer);
  sliderBusy = false;
  api("load", Number(el("load-slider").value));
});
refresh();
setInterval(refresh, 250);
