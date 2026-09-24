/**
 * Main JavaScript file for client-side API verification and interaction.
 */

const API_BASE_URL = (() => {
    const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    if (isLocalhost && window.location.port !== "5000" && window.location.port !== "") {
        return "http://127.0.0.1:5000";
    }
    return window.location.origin;
})();

document.addEventListener("DOMContentLoaded", () => {
    const checkHealthBtn = document.getElementById("check-health-btn");
    const statusBadge = document.getElementById("status-badge");
    const outputContainer = document.getElementById("api-response-output");

    if (checkHealthBtn) {
        checkHealthBtn.addEventListener("click", () => {
            fetchHealthStatus(statusBadge, outputContainer);
        });

        // Automatically ping on page load
        fetchHealthStatus(statusBadge, outputContainer);
    }
});

async function fetchHealthStatus(badgeElement, outputElement) {
    if (!badgeElement || !outputElement) return;

    badgeElement.className = "badge bg-warning text-dark";
    badgeElement.textContent = "Connecting...";
    outputElement.textContent = "Sending request to " + API_BASE_URL + "/api/health...";

    try {
        const response = await fetch(`${API_BASE_URL}/api/health`, {
            method: "GET",
            headers: {
                "Accept": "application/json"
            }
        });

        const data = await response.json();

        if (response.ok) {
            badgeElement.className = "badge bg-success";
            badgeElement.textContent = "Online (HTTP 200)";
            outputElement.className = "mb-0 text-success";
            outputElement.textContent = JSON.stringify(data, null, 2);
        } else {
            badgeElement.className = "badge bg-danger";
            badgeElement.textContent = `Error ${response.status}`;
            outputElement.className = "mb-0 text-danger";
            outputElement.textContent = JSON.stringify(data, null, 2);
        }
    } catch (error) {
        badgeElement.className = "badge bg-danger";
        badgeElement.textContent = "Offline / Unreachable";
        outputElement.className = "mb-0 text-danger";
        outputElement.textContent = `Could not connect to ${API_BASE_URL}/api/health.\nMake sure the Flask server is running (e.g. 'python backend/app.py') and CORS is enabled.\nError: ${error.message}`;
    }
}
