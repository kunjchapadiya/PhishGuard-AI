# 🛡️ PhishGuard AI - Chrome Extension & ML Backend

PhishGuard AI is an AI-powered phishing and malicious URL protection system consisting of a Google Chrome Extension (Manifest V3) and a high-performance Flask Machine Learning backend API.

---

## 📁 Clean Project Structure

```text
PhishGuard AI/
├── extension/                     # 🧩 CHROME EXTENSION (Load this folder in Chrome)
│   ├── manifest.json              # Manifest V3 configuration & permissions
│   ├── popup.html                 # Extension popup interface
│   ├── popup.css                  # Modern cybersecurity dark theme styling
│   ├── popup.js                   # Tab inspector & API integration logic
│   ├── background.js              # Background service worker for tab protection
│   ├── options.html               # Settings page (switch between Local & Cloud API)
│   ├── options.js                 # Settings save & test connection logic
│   ├── icons/                     # Shield icons (16px, 48px, 128px)
│   └── README.md                  # Extension installation guide
│
├── app.py                         # ⚡ FLASK API BACKEND (Serves /predict to extension)
├── feature_extractor.py           # 13-feature lexical & structural extractor
├── predictor.py                   # Model pipeline loader & probability scorer
├── requirements.txt               # Dependencies (Flask, scikit-learn, etc.)
│
├── models/                        # 🧠 TRAINED MACHINE LEARNING ARTIFACTS
│   ├── phishguard_pipeline.pkl    # Serialized Random Forest (97.4% accuracy)
│   └── model_metadata.json        # Model metrics & specs
│
├── Procfile                       # Deployment config for Render / Railway
└── render.yaml                    # Render deployment blueprint
```

---

## 🚀 How to Run

### Step 1: Live Cloud Backend API
The backend is deployed and live at:
```text
https://phishguard-ai-46qm.onrender.com/
```
*(Optional) To run locally instead: `python app.py` on `http://127.0.0.1:5000`.*

### Step 2: Load Extension in Chrome
1. In Google Chrome, go to `chrome://extensions/`
2. Turn **ON** the **Developer mode** toggle (top-right).
3. Click **"Load unpacked"** (top-left).
4. Select the `extension` folder:
   `c:\Users\Admin\ML Practice\DS Projects\PhishGuard AI\extension`
5. Pin **PhishGuard AI** to your browser toolbar and click it on any website to scan!

---

## 📊 Model Evaluation & Confusion Matrix

Evaluated on 10,000 unseen test URLs:

| Actual \ Predicted | Predicted Phishing | Predicted Legitimate | Total |
| :--- | :---: | :---: | :---: |
| **Actual Phishing** | **2,936** *(True Phish)* | **231** *(Missed)* | 3,167 |
| **Actual Legitimate** | **95** *(False Alarm)* | **6,738** *(True Safe)* | 6,833 |
| **Total** | 3,031 | 6,969 | **10,000** |

- **Accuracy**: **96.74%**
- **Weighted F1-Score**: **96.72%**
- **Phishing Detection Recall**: **92.71%**
- **Legitimate Site Precision**: **96.69%**

---

## ☁️ Cloud Deployment (Render / Railway)
The backend service is currently hosted on Render:
- **Live Endpoint**: `https://phishguard-ai-46qm.onrender.com/`
- **Health Check**: `https://phishguard-ai-46qm.onrender.com/health`

To change or update your backend URL, configure `.env` (`BACKEND_API='https://phishguard-ai-46qm.onrender.com/'`) or use the extension Settings page.

