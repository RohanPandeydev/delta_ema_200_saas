// WebSocket connection for real-time logs
const socket = io();

// Connect to SocketIO
socket.on("connect", () => {
  console.log("Connected to WebSocket");
});

socket.on("connected", (data) => {
  console.log(data);
});

// Subscribe to logs for a specific container
function subscribeLogs(containerId) {
  socket.emit("subscribe_logs", { container_id: containerId });
}

socket.on("subscribed", (data) => {
  console.log("Subscribed to logs for container:", data.container_id);
});

// Receive log updates
socket.on("log_update", (data) => {
  const logsContainer = document.getElementById("logs-output");
  if (logsContainer) {
    const logLine = document.createElement("div");
    logLine.className = "log-line";
    logLine.textContent = data.log;
    logsContainer.appendChild(logLine);

    // Auto-scroll to bottom
    logsContainer.scrollTop = logsContainer.scrollHeight;
  }
});

// Fetch logs via AJAX
function fetchLogs(containerId) {
  fetch(`/dashboard/api/container/${containerId}/logs`)
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        const logsContainer = document.getElementById("logs-output");
        logsContainer.innerHTML = "";

        data.logs.forEach((log) => {
          const logLine = document.createElement("div");
          logLine.className = "log-line";
          logLine.textContent = log;
          logsContainer.appendChild(logLine);
        });

        logsContainer.scrollTop = logsContainer.scrollHeight;
      }
    })
    .catch((error) => console.error("Error fetching logs:", error));
}

// Auto-refresh logs every 5 seconds
let logRefreshInterval;

function startLogRefresh(containerId) {
  fetchLogs(containerId);
  logRefreshInterval = setInterval(() => {
    fetchLogs(containerId);
  }, 5000);
}

function stopLogRefresh() {
  if (logRefreshInterval) {
    clearInterval(logRefreshInterval);
  }
}

// Modal functions
function openModal(modalId) {
  document.getElementById(modalId).classList.add("active");
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.remove("active");
}

// Confirm actions
function confirmAction(message, callback) {
  if (confirm(message)) {
    callback();
  }
}

// Flash message auto-hide
document.addEventListener("DOMContentLoaded", () => {
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach((alert) => {
    setTimeout(() => {
      alert.style.opacity = "0";
      setTimeout(() => alert.remove(), 300);
    }, 5000);
  });
});
