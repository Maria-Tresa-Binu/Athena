const messages = document.querySelector("#messages");
const briefing = document.querySelector("#briefing");
const form = document.querySelector("#composer");
const input = document.querySelector("#input");
const status = document.querySelector("#status");
const activate = document.querySelector("#activate");
const mic = document.querySelector("#mic");
const voiceSelect = document.querySelector("#voice");
let availableVoices = [];

function setStatus(label, active = false) {
  status.classList.toggle("active", active);
  status.querySelector("span:last-child").textContent = label;
  document.body.classList.toggle("processing", active);
}

function addMessage(text, who) {
  const row = document.createElement("div");
  row.className = `message ${who}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  row.appendChild(bubble);
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
}

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(cleanSpeechText(text));
  const selectedName = localStorage.getItem("athenaVoice");
  const voice = availableVoices.find((item) => item.name === selectedName) || availableVoices.find((item) => /aria|jenny|zira|hazel|susan|female|natural/i.test(item.name));
  if (voice) utterance.voice = voice;
  utterance.rate = 1;
  utterance.pitch = 1.05;
  window.speechSynthesis.speak(utterance);
}

function cleanSpeechText(text) {
  return text
    .replace(/https?:\/\/\S+|www\.\S+/gi, "")
    .replace(/```[\s\S]*?```/g, "")
    .replace(/[\*_`#{}\[\]<>|"“”]/g, " ")
    .replace(/&/g, " and ")
    .replace(/@/g, " at ")
    .replace(/[\\/]/g, " ")
    .replace(/[–—-]+/g, " ")
    .replace(/[^\p{L}\p{N}\s.,?!:;']/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function loadVoices() {
  availableVoices = window.speechSynthesis.getVoices().filter((voice) => voice.lang.toLowerCase().startsWith("en"));
  voiceSelect.innerHTML = "";
  availableVoices.forEach((voice) => {
    const option = document.createElement("option");
    option.value = voice.name;
    option.textContent = voice.name;
    voiceSelect.appendChild(option);
  });
  const preferred = localStorage.getItem("athenaVoice") || availableVoices.find((voice) => /aria|jenny|natural/i.test(voice.name))?.name;
  if (preferred) voiceSelect.value = preferred;
}

voiceSelect.addEventListener("change", () => localStorage.setItem("athenaVoice", voiceSelect.value));
if ("speechSynthesis" in window) { loadVoices(); window.speechSynthesis.onvoiceschanged = loadVoices; }

function showBriefing(text) {
  briefing.innerHTML = "";
  const card = document.createElement("article");
  card.className = "briefing-card ready";
  const heading = document.createElement("div");
  heading.className = "card-heading";
  heading.innerHTML = "<span>◈</span> DAILY INTELLIGENCE BRIEFING";
  const body = document.createElement("div");
  body.className = "card-body";
  body.textContent = text;
  card.append(heading, body);
  briefing.appendChild(card);
}

async function readApiResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return response.json();
  const body = (await response.text()).replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
  throw new Error(`Server returned ${response.status}${body ? `: ${body.slice(0, 180)}` : ""}`);
}

async function activateAthena() {
  activate.disabled = true;
  activate.querySelector(".core-state").textContent = "SCANNING";
  setStatus("FETCHING EMAIL // CALENDAR // NEWS", true);
  briefing.innerHTML = '<div class="briefing-card loading"><div class="card-heading"><span>◈</span> SYNCHRONIZING SOURCES</div><div class="loader"></div></div>';
  try {
    const response = await fetch("/api/briefing", { method: "POST" });
    const data = await readApiResponse(response);
    if (!response.ok) throw new Error(data.detail || "Briefing failed");
    showBriefing(data.response);
    addMessage(data.response, "athena");
    speak(data.response);
    activate.querySelector(".core-state").textContent = "ONLINE";
    setStatus("BRIEFING COMPLETE // ATHENA ONLINE");
  } catch (error) {
    showBriefing(`Connection error: ${error.message}`);
    activate.querySelector(".core-state").textContent = "ERROR";
    setStatus("CONNECTION ERROR");
  } finally { activate.disabled = false; }
}

async function send(message) {
  addMessage(message, "user");
  input.value = "";
  setStatus("PROCESSING REQUEST", true);
  try {
    const response = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message }) });
    const data = await readApiResponse(response);
    if (!response.ok) throw new Error(data.detail || "Request failed");
    addMessage(data.response, "athena");
    speak(data.response);
    setStatus("ATHENA ONLINE");
  } catch (error) { addMessage(`Connection error: ${error.message}`, "athena"); setStatus("DISCONNECTED"); }
}

activate.addEventListener("click", activateAthena);
form.addEventListener("submit", (event) => { event.preventDefault(); if (input.value.trim()) send(input.value.trim()); });
document.querySelector("#reset").addEventListener("click", async () => { await fetch("/api/reset", { method: "POST" }); messages.innerHTML = ""; briefing.innerHTML = '<div class="briefing-empty">Activate Athena for your daily intelligence briefing.</div>'; activate.querySelector(".core-state").textContent = "STANDBY"; setStatus("STANDBY // READY"); speak("Conversation cleared. I’m ready."); });

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (Recognition) {
  const recognition = new Recognition();
  recognition.lang = navigator.language || "en-US";
  recognition.interimResults = false;
  mic.addEventListener("click", () => { setStatus("LISTENING", true); recognition.start(); });
  recognition.onresult = (event) => send(event.results[0][0].transcript);
  recognition.onerror = () => setStatus("MICROPHONE UNAVAILABLE");
} else { mic.disabled = true; mic.title = "Speech recognition is not supported by this browser"; }
