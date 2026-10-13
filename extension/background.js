// ==========================================================================
// PhishGuard AI - Background Service Worker
// Automatically monitors visited tabs and alerts user of phishing threats
// ==========================================================================

const DEFAULT_API_URL = "https://phishguard-ai-46qm.onrender.com";
const DEFAULT_NOTIFICATION_THRESHOLD = 90; // Confidence threshold in % (above 90%)

// Prevent duplicate spam notifications for the same URL in short intervals
const notifiedUrls = new Set();

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
    // Only inspect when page URL finishes loading
    if (changeInfo.status === 'complete' && tab.url) {
        const url = tab.url;

        // Skip non-web protocols
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            chrome.action.setBadgeText({ text: '', tabId });
            return;
        }

        try {
            const settings = await chrome.storage.sync.get({
                apiUrl: DEFAULT_API_URL,
                autoProtect: true,
                notificationThreshold: DEFAULT_NOTIFICATION_THRESHOLD
            });

            if (settings.apiUrl === "http://127.0.0.1:5000" || settings.apiUrl === "http://localhost:5000") {
                settings.apiUrl = DEFAULT_API_URL;
                chrome.storage.sync.set({ apiUrl: DEFAULT_API_URL });
            }

            if (!settings.autoProtect) return;

            const apiUrl = settings.apiUrl.replace(/\/+$/, '');
            const response = await fetch(`${apiUrl}/predict`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            if (!response.ok) return;

            const json = await response.json();
            if (json.success && json.data) {
                const data = json.data;
                const isPhish = data.is_phishing;
                const phishingProbPercent = (data.phishing_probability * 100);
                const threshold = Number(settings.notificationThreshold) || DEFAULT_NOTIFICATION_THRESHOLD;

                // Only show error badge & send notification if phishing confidence is >= threshold (90%)
                if (isPhish && phishingProbPercent >= threshold) {
                    // Show error icon on extension
                    chrome.action.setBadgeText({ text: '!', tabId });
                    chrome.action.setBadgeBackgroundColor({ color: '#ef4444', tabId });

                    // Send desktop notification
                    const urlKey = `${tabId}:${url}`;
                    if (!notifiedUrls.has(urlKey)) {
                        notifiedUrls.add(urlKey);
                        setTimeout(() => notifiedUrls.delete(urlKey), 30000); // Reset after 30s

                        chrome.notifications.create({
                            type: 'basic',
                            iconUrl: 'icons/icon48.png',
                            title: '🚨 High-Risk Phishing Alert!',
                            message: `Dangerous link detected (${phishingProbPercent.toFixed(1)}% confidence):\n${url.substring(0, 60)}...`,
                            priority: 2
                        });
                    }
                } else {
                    // Otherwise, do not show any error icon on extension
                    chrome.action.setBadgeText({ text: '', tabId });
                }
            }
        } catch (err) {
            // Backend offline or unreachable
            chrome.action.setBadgeText({ text: '', tabId });
        }
    }
});
