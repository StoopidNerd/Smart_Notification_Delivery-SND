# 🚀 Geo-Deferred Notification System (SND)

> **Smart notification delivery based on signal strength & priority**

---

## 🧠 Problem

* Notifications arrive in weak networks
* Important alerts may fail or delay
* Unnecessary messages waste battery

👉 **Solution:** Deliver notifications at the *right time* based on signal + priority

---

## ⚙️ Key Features

* Priority-based delivery (URGENT, HIGH, NORMAL, LOW)
* Signal-aware system (GREEN, YELLOW, RED)
* Smart deferral + retry with backoff
* Queue-based processing
* Real-time WebSocket updates
* AI-based priority assignment
* Trip simulation + geo-based zones

---

## 🧱 Tech Stack

**Backend:** FastAPI, SQLite, Python asyncio, API Key Auth
**Frontend:** HTML, CSS, JS (Real-time dashboard via WebSockets)

---

## 🏗 Architecture

```
User → FastAPI → Queue → Decision Engine → Delivery
                     ↓
                 Signal Engine
                     ↓
               WebSocket → UI
```

---

## 🔄 How It Works

1. Notification created (`/notifications`)
2. Priority assigned (AI/manual)
3. Signal checked (GREEN/YELLOW/RED)
4. Decision → Deliver or Defer
5. Retry engine ensures delivery
6. Live updates via WebSocket

---

## 📡 Signal Rules

| Priority | Allowed Signal     |
| -------- | ------------------ |
| URGENT   | GREEN, YELLOW, RED |
| HIGH     | GREEN, YELLOW      |
| NORMAL   | GREEN              |
| LOW      | GREEN              |

---

## ▶️ Run Locally

```bash
pip install fastapi uvicorn
python -m server:app --reload
```

Open → [http://127.0.0.1:8000](http://127.0.0.1:8000)

**Auth:**
`Authorization: Bearer Team201A`

---

## 📡 APIs

* `POST /notifications` → create notification
* `POST /location` → update signal/location
* `POST /trip/simulate` → simulate drive
* `GET /analytics` → system insights

---

## 🔌 WebSocket Events

* notification_created
* notification_delivered
* notification_deferred
* notification_retrying
* notification_failed
* position_update

---

## 🎯 Use Cases

* Connected vehicles 🚗
* Emergency alerts 🚑
* Rural network optimization 📡
* Battery-efficient notifications 📲

---

## 🧠 Core Concepts

Priority queues • Event-driven system • WebSockets • Retry logic • Geo-based decisions

---

## 🚀 Future  Scope

* ML-based prediction
* Mobile app integration
* Advanced analytics
* Real map APIs

---

Preview of the website
<img width="1906" height="918" alt="Screenshot 2026-04-19 083059" src="https://github.com/user-attachments/assets/522ecde5-ca87-479d-80ec-f7eac5f792da" />
<img width="1903" height="908" alt="Screenshot 2026-04-19 083038" src="https://github.com/user-attachments/assets/8aaf4ae6-5a82-446e-abe0-7f9ce3b0073a" />
<img width="1909" height="898" alt="Screenshot 2026-04-19 083008" src="https://github.com/user-attachments/assets/9f402288-529e-4601-9948-ace0a46daeac" />
<img width="1887" height="905" alt="Screenshot 2026-04-19 082939" src="https://github.com/user-attachments/assets/7a208e36-1b93-4e33-8b10-1e676ded773b" />
<img width="1901" height="900" alt="Screenshot 2026-04-19 082909" src="https://github.com/user-attachments/assets/65c4ad64-9107-4244-bdce-63f8ecd2670e" />


## 🏁 Summary

> **Delivers the right notification at the right time using signal awareness + priority logic**
