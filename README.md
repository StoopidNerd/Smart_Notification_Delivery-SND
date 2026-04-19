🚀 Geo-Deferred Notification System (SND)

Smart notification delivery based on signal strength & priority

🧠 Problem
Notifications arrive in weak networks
Important alerts may fail or delay
Unnecessary messages waste battery

👉 Solution: Deliver notifications at the right time based on signal + priority

⚙️ Key Features
Priority-based delivery (URGENT, HIGH, NORMAL, LOW)
Signal-aware system (GREEN, YELLOW, RED)
Smart deferral + retry with backoff
Queue-based processing
Real-time WebSocket updates
AI-based priority assignment
Trip simulation + geo-based zones
🧱 Tech Stack

Backend: FastAPI, SQLite, Python asyncio, API Key Auth
Frontend: HTML, CSS, JS (Real-time dashboard via WebSockets)

🏗 Architecture
User → FastAPI → Queue → Decision Engine → Delivery
                     ↓
                 Signal Engine
                     ↓
               WebSocket → UI
🔄 How It Works
Notification created (/notifications)
Priority assigned (AI/manual)
Signal checked (GREEN/YELLOW/RED)
Decision → Deliver or Defer
Retry engine ensures delivery
Live updates via WebSocket
📡 Signal Rules
Priority	Allowed Signal
URGENT	GREEN, YELLOW, RED
HIGH	GREEN, YELLOW
NORMAL	GREEN
LOW	GREEN
▶️ Run Locally
pip install fastapi uvicorn
python -m server:app --reload

Open → http://127.0.0.1:8000

Auth:
Authorization: Bearer Team201A

📡 APIs
POST /notifications → create notification
POST /location → update signal/location
POST /trip/simulate → simulate drive
GET /analytics → system insights
🔌 WebSocket Events
notification_created
notification_delivered
notification_deferred
notification_retrying
notification_failed
position_update
🎯 Use Cases
Connected vehicles 🚗
Emergency alerts 🚑
Rural network optimization 📡
Battery-efficient notifications 📲
🧠 Core Concepts

Priority queues • Event-driven system • WebSockets • Retry logic • Geo-based decisions

🚀 Future Scope
ML-based prediction
Mobile app integration
Advanced analytics
Real map APIs
🏁 Summary

Delivers the right notification at the right time using signal awareness + priority logic
