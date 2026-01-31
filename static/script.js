const WS_URL = "ws://localhost:8765";
let ws = null;
let reconnectDelay = 1000;

function connect() {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        reconnectDelay = 1000;
        setStatus(true);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        render(data);
    };

    ws.onclose = () => {
        setStatus(false);
        setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 5000);
    };

    ws.onerror = () => {
        ws.close();
    };
}

function setStatus(connected) {
    const el = document.getElementById("status");
    el.textContent = connected ? "Connected" : "Reconnecting...";
    el.className = connected ? "connected" : "disconnected";
}

function render(data) {
    const tbody = document.getElementById("data-body");
    tbody.innerHTML = "";

    for (const [key, value] of Object.entries(data)) {
        const row = document.createElement("tr");
        row.innerHTML = `<td>${key}</td><td>${value}</td>`;
        tbody.appendChild(row);
    }
}

connect();
