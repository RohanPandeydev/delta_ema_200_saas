// Initialize socket connection
const socket = io();
let activeLogStreams = new Set();
let currentBotId = null;

// Connection handlers
socket.on("connect", () => {
  console.log("Connected to WebSocket server");
  const statusEl = document.getElementById("connectionStatus");
  if (statusEl) {
    statusEl.textContent = "● CONNECTED";
    statusEl.className = "badge bg-success ms-2";
  }
});

socket.on("connected", (data) => {
  console.log(data.data);
});

socket.on("disconnect", () => {
  console.log("Disconnected from WebSocket server");
  activeLogStreams.clear();
  const statusEl = document.getElementById("connectionStatus");
  if (statusEl) {
    statusEl.textContent = "● DISCONNECTED";
    statusEl.className = "badge bg-secondary ms-2";
  }
});

// Log streaming handlers
socket.on("log_update", (data) => {
  if (data.bot_id === currentBotId) {
    const logsContent = document.getElementById("logsContent");
    if (logsContent) {
      const logLine = document.createElement("div");
      logLine.className = "log-line";
      logLine.textContent = data.log_line;
      logsContent.appendChild(logLine);

      // Auto-scroll to bottom
      logsContent.scrollTop = logsContent.scrollHeight;
    }
  }
});

socket.on("stream_started", (data) => {
  console.log(`Log stream started for bot ${data.bot_id}`);
  activeLogStreams.add(data.bot_id);

  // Update UI to show streaming status
  const statusEl = document.getElementById(`stream-status-${data.bot_id}`);
  if (statusEl) {
    statusEl.textContent = "🟢 Live";
    statusEl.classList.add("streaming");
  }
});

socket.on("stream_stopped", (data) => {
  console.log(`Log stream stopped for bot ${data.bot_id}`);
  activeLogStreams.delete(data.bot_id);

  // Update UI to show stopped status
  const statusEl = document.getElementById(`stream-status-${data.bot_id}`);
  if (statusEl) {
    statusEl.textContent = "⚫ Stopped";
    statusEl.classList.remove("streaming");
  }
});

socket.on("error", (data) => {
  console.error("WebSocket error:", data.message);
  if (data.bot_id) {
    const logContainer = document.getElementById(`logs-${data.bot_id}`);
    if (logContainer) {
      const errorLine = document.createElement("div");
      errorLine.className = "error-log";
      errorLine.textContent = `Error: ${data.message}`;
      logContainer.appendChild(errorLine);
    }
  }
});

// Functions to control log streaming
function startLogStream(botId) {
  // Stop any existing stream
  stopLogStream(currentBotId);

  // Set new bot id and start stream
  currentBotId = botId;
  activeLogStreams.add(botId);
  socket.emit("start_log_stream", { bot_id: botId });

  // Update status
  const statusEl = document.getElementById("connectionStatus");
  if (statusEl) {
    statusEl.textContent = "● LIVE";
    statusEl.className = "badge bg-success ms-2 streaming";
  }
}

function stopLogStream(botId) {
  if (botId && activeLogStreams.has(botId)) {
    socket.emit("stop_log_stream", { bot_id: botId });
    activeLogStreams.delete(botId);

    // Update status
    const statusEl = document.getElementById("connectionStatus");
    if (statusEl) {
      statusEl.textContent = "● OFFLINE";
      statusEl.className = "badge bg-danger ms-2";
    }

    if (botId === currentBotId) {
      currentBotId = null;
    }
  }
}

// Clean up when leaving page
window.addEventListener("beforeunload", () => {
  activeLogStreams.forEach((botId) => {
    stopLogStream(botId);
  });
});
