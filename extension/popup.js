// ==========================================================================
// PhishGuard AI - Extension Popup Logic
// ==========================================================================

const DEFAULT_API_URL = "https://phishguard-ai-46qm.onrender.com";

document.addEventListener('DOMContentLoaded', async () => {
    // 1. DOM Elements
    const siteDomainEl = document.getElementById('site-domain');
    const siteUrlEl = document.getElementById('site-url');
    const scanBtn = document.getElementById('scan-btn');
    const spinner = document.getElementById('spinner');
    const resultBox = document.getElementById('result-box');
    const verdictBadge = document.getElementById('verdict-badge');
    const verdictTitle = document.getElementById('verdict-title');
    const verdictSubtitle = document.getElementById('verdict-subtitle');
    const probPercentage = document.getElementById('prob-percentage');
    const meterBar = document.getElementById('meter-bar');
    const riskLevel = document.getElementById('risk-level');
    const confidenceVal = document.getElementById('confidence-val');
    const apiDot = document.getElementById('api-dot');
    const apiText = document.getElementById('api-text');

    const featHttps = document.getElementById('feat-https');
    const featLength = document.getElementById('feat-length');
    const featTld = document.getElementById('feat-tld');
    const featDepth = document.getElementById('feat-depth');

    const toggleManualBtn = document.getElementById('toggle-manual-btn');
    const manualInputBox = document.getElementById('manual-input-box');
    const manualUrlInput = document.getElementById('manual-url');
    const manualScanBtn = document.getElementById('manual-scan-btn');

    let currentTabUrl = "";

    // 2. Load API URL setting from chrome.storage
    const settings = await chrome.storage.sync.get({ apiUrl: DEFAULT_API_URL, autoScan: true });
    if (settings.apiUrl === "http://127.0.0.1:5000" || settings.apiUrl === "http://localhost:5000") {
        settings.apiUrl = DEFAULT_API_URL;
        chrome.storage.sync.set({ apiUrl: DEFAULT_API_URL });
    }
    const apiUrl = settings.apiUrl.replace(/\/+$/, '');

    // Display formatted API host in footer
    try {
        const u = new URL(apiUrl);
        apiText.textContent = `API: ${u.host}`;
    } catch {
        apiText.textContent = `API: ${apiUrl}`;
    }

    // 3. Query current active tab
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.url) {
            currentTabUrl = tab.url;
            siteUrlEl.textContent = currentTabUrl;
            siteUrlEl.title = currentTabUrl;

            try {
                const parsed = new URL(currentTabUrl);
                siteDomainEl.textContent = parsed.hostname || "Internal Browser Page";
            } catch {
                siteDomainEl.textContent = currentTabUrl.substring(0, 30);
            }

            // Don't auto-scan browser internal chrome:// or extension:// pages
            if (currentTabUrl.startsWith("http://") || currentTabUrl.startsWith("https://")) {
                if (settings.autoScan) {
                    analyzeUrl(currentTabUrl);
                }
            } else {
                siteDomainEl.textContent = "Browser Internal Page";
                scanBtn.disabled = true;
            }
        } else {
            siteDomainEl.textContent = "No active web page";
            scanBtn.disabled = true;
        }
    } catch (err) {
        console.error("Could not query active tab:", err);
        siteDomainEl.textContent = "Unable to read tab URL";
    }

    // 4. Scan Button Event
    scanBtn.addEventListener('click', () => {
        if (currentTabUrl) {
            analyzeUrl(currentTabUrl);
        }
    });

    // 5. Manual Scan Toggle
    toggleManualBtn.addEventListener('click', () => {
        manualInputBox.classList.toggle('hidden');
    });

    manualScanBtn.addEventListener('click', () => {
        const customUrl = manualUrlInput.value.trim();
        if (customUrl) {
            analyzeUrl(customUrl);
        }
    });

    // 6. API Prediction Request Function
    async function analyzeUrl(targetUrl) {
        setLoading(true);
        resultBox.classList.remove('hidden');

        try {
            const endpoint = `${apiUrl}/predict`;
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: targetUrl })
            });

            if (!response.ok) {
                const errJson = await response.json().catch(() => ({}));
                throw new Error(errJson.error || `Server returned HTTP ${response.status}`);
            }

            const json = await response.json();
            if (!json.success || !json.data) {
                throw new Error(json.error || "Invalid response format from API");
            }

            apiDot.className = 'dot'; // Green dot
            renderResults(json.data);

        } catch (err) {
            console.error("PhishGuard API Connection Error:", err);
            apiDot.className = 'dot offline'; // Red dot

            verdictBadge.textContent = 'ERROR';
            verdictBadge.className = 'verdict-badge threat';
            verdictTitle.textContent = 'API Offline';
            verdictSubtitle.textContent = `Could not reach ${apiUrl}. Make sure 'python app.py' is running!`;

            meterBar.style.width = '0%';
            probPercentage.textContent = 'N/A';
            riskLevel.textContent = 'Offline';
            confidenceVal.textContent = 'N/A';

            featHttps.textContent = '-';
            featLength.textContent = '-';
            featTld.textContent = '-';
            featDepth.textContent = '-';
        } finally {
            setLoading(false);
        }
    }

    function renderResults(data) {
        const isPhish = data.is_phishing;
        const prob = (data.phishing_probability * 100).toFixed(1);
        const conf = (data.confidence_score * 100).toFixed(0);

        if (isPhish) {
            verdictBadge.textContent = 'THREAT';
            verdictBadge.className = 'verdict-badge threat';
            if (parseFloat(prob) >= 90) {
                verdictTitle.textContent = 'High-Risk Phishing (>90%)';
                verdictSubtitle.textContent = 'Critical threat confidence: alert notification triggered';
            } else {
                verdictTitle.textContent = 'Suspicious Link';
                verdictSubtitle.textContent = 'Moderate threat confidence (<90% threshold, silent badge)';
            }
            meterBar.style.backgroundColor = '#ef4444';
        } else {
            verdictBadge.textContent = 'SAFE';
            verdictBadge.className = 'verdict-badge safe';
            verdictTitle.textContent = 'Legitimate Website';
            verdictSubtitle.textContent = 'Verified structural authenticity';
            meterBar.style.backgroundColor = '#10b981';
        }

        meterBar.style.width = Math.max(parseFloat(prob), 5) + '%';
        probPercentage.textContent = prob + '%';
        riskLevel.textContent = data.risk_level || (isPhish ? 'High' : 'Low');
        confidenceVal.textContent = conf + '%';

        // Features summary
        const f = data.features || {};
        featHttps.textContent = f.isHTTP ? 'Yes' : 'No';
        featLength.textContent = f.length || targetUrl.length;
        featTld.textContent = f.TLD ? `.${f.TLD}` : 'None';
        featDepth.textContent = f.path_depth !== undefined ? f.path_depth : 0;
    }

    function setLoading(isLoading) {
        scanBtn.disabled = isLoading;
        if (isLoading) {
            spinner.classList.remove('hidden');
        } else {
            spinner.classList.add('hidden');
        }
    }
});
