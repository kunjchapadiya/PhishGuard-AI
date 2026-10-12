# 🧩 PhishGuard AI - Chrome Extension

Real-time browser extension that monitors URLs and flags phishing threats using the PhishGuard AI backend.

---

## ❓ Do I have to deploy the backend to Render/Railway?

- **For testing & local use on your computer:** **NO.**
  As long as your Flask server is running locally (`python app.py`), the extension will communicate directly with `http://127.0.0.1:5000`.
- **For sharing with others or publishing to Chrome Web Store:** **YES.**
  To let anyone use your extension without having your personal computer running, deploy the backend to Render, Railway, or AWS, and update the API URL in the extension settings.

---

## 🚀 How to Install and Run the Extension (Local Mode)

### 1. Generate Extension Icons
In your terminal, run:
```bash
python create_extension_icons.py
```
This generates `icon16.png`, `icon48.png`, and `icon128.png` in the `extension/icons/` folder.

### 2. Load the Extension in Google Chrome
1. Open Google Chrome and type in the address bar:
   ```text
   chrome://extensions/
   ```
2. In the top-right corner, turn **ON** the **Developer mode** toggle.
3. Click the **"Load unpacked"** button in the top-left corner.
4. Select the `extension` directory from your project:
   `c:\Users\Admin\ML Practice\DS Projects\PhishGuard AI\extension`
5. The **PhishGuard AI** extension is now installed! Pin it to your Chrome toolbar.

### 3. Test It
1. Ensure your Flask server is running:
   ```bash
   python app.py
   ```
2. Browse to any website (e.g. `https://google.com` or any link).
3. Click the **PhishGuard AI** shield icon in Chrome.
4. Click **"Scan Current Tab"** to inspect the real-time AI threat verdict!

---

## ☁️ How to Deploy Backend to Cloud (Render / Railway)

When you are ready to publish or share the extension:

### Option A: Render.com (Free Tier)
1. Push this project to GitHub.
2. Sign in to [Render](https://render.com) and click **"New +"** &rarr; **"Web Service"**.
3. Select your repository.
4. Render will automatically detect the `Procfile` and `requirements.txt`:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 2 -b 0.0.0.0:$PORT app:app`
5. Click **Create Web Service**.
6. Once deployed, copy your service URL:
   `https://your-phishguard-api.onrender.com`
7. In the Chrome extension, click the **Settings gear icon** &rarr; paste your Render URL &rarr; click **Save Settings**!

### Option B: Railway.app
1. Sign in to [Railway](https://railway.app) and click **New Project** &rarr; **Deploy from GitHub repo**.
2. Railway will automatically build and expose the port.
3. Copy the public Railway URL into the extension settings.
