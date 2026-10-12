// ==========================================================================
// PhishGuard AI - Extension Options Logic
// ==========================================================================

const DEFAULT_API_URL = "http://127.0.0.1:5000";
const DEFAULT_THRESHOLD = 90;

document.addEventListener('DOMContentLoaded', async () => {
    const apiUrlInput = document.getElementById('api-url');
    const thresholdInput = document.getElementById('threshold');
    const autoProtectInput = document.getElementById('auto-protect');
    const settingsForm = document.getElementById('settings-form');
    const testBtn = document.getElementById('test-btn');
    const statusBox = document.getElementById('status-box');

    // Load saved settings
    const data = await chrome.storage.sync.get({
        apiUrl: DEFAULT_API_URL,
        autoProtect: true,
        notificationThreshold: DEFAULT_THRESHOLD
    });

    apiUrlInput.value = data.apiUrl;
    thresholdInput.value = data.notificationThreshold;
    autoProtectInput.checked = data.autoProtect;

    // Save settings
    settingsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const newUrl = apiUrlInput.value.trim().replace(/\/+$/, '');
        const newThreshold = Math.min(100, Math.max(50, Number(thresholdInput.value) || DEFAULT_THRESHOLD));
        const autoProtect = autoProtectInput.checked;

        await chrome.storage.sync.set({
            apiUrl: newUrl,
            notificationThreshold: newThreshold,
            autoProtect: autoProtect
        });

        showMessage(`Settings saved! Alerts will only trigger when phishing confidence is above ${newThreshold}%.`, "success");
    });

    // Test connection
    testBtn.addEventListener('click', async () => {
        const testUrl = apiUrlInput.value.trim().replace(/\/+$/, '');
        showMessage(`Pinging ${testUrl}/health...`, "success");

        try {
            const res = await fetch(`${testUrl}/health`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();

            if (json.status === "healthy") {
                showMessage(`✅ Connection successful! Service: ${json.service} | Model Loaded: ${json.model_loaded}`, "success");
            } else {
                showMessage(`⚠️ API responded, but reported: ${JSON.stringify(json)}`, "error");
            }
        } catch (err) {
            showMessage(`❌ Connection failed to ${testUrl}. Ensure 'python app.py' is running. Error: ${err.message}`, "error");
        }
    });

    function showMessage(msg, type) {
        statusBox.textContent = msg;
        statusBox.className = `status-msg ${type}`;
    }
});
