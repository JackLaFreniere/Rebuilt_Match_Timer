const ws = new WebSocket("ws://127.0.0.1:8765");
const statusEl = document.getElementById("status");
const dataEl = document.getElementById("data");

ws.onopen = () => {
    statusEl.textContent = "Connected";
    statusEl.className = "connected";
    console.log("WebSocket connected");
};

ws.onmessage = (event) => {
    console.log("Received:", event.data);
    const data = JSON.parse(event.data);
    
    dataEl.innerHTML = "";
    for (const [key, value] of Object.entries(data)) {
        const row = document.createElement("tr");
        row.innerHTML = `<td>${key}</td><td>${value}</td>`;
        dataEl.appendChild(row);
    }
};

ws.onclose = () => {
    statusEl.textContent = "Disconnected";
    statusEl.className = "";
    console.log("WebSocket disconnected");
};

ws.onerror = (error) => {
    console.log("WebSocket error:", error);
};
