--- # 🚀 Geo-Deferred Notification System (SND)

> **Smart Notification Delivery based on Signal Strength & Priority**

A system that intelligently delays or delivers notifications based on network conditions and message importance.

---

## 🧠 Problem Statement

In real-life situations:

* Notifications arrive when the network is weak.

* Important alerts may. Get delayed.

* Unnecessary notifications waste. Battery.

👉 **Solution:**

A system that decides *when* to deliver notifications, not just *how*.

---

## ⚙️ Key Features

### 🔥 Core System

* ✅ Priority-based notification handling (URGENT, HIGH, NORMAL, LOW).

* ✅ Signal-aware delivery (GREEN, YELLOW, RED zones).

* ✅ Smart deferral (waits for network).

* ✅ Retry engine with backoff.

* ✅ Queue-based delivery system.

---

### ⚡ Real-Time Features

* 🔌 WebSocket-based updates.

* 📡 Live signal tracking.

* 📊 Real-time dashboard UI.

* 🔄 Auto queue flushing when signal improves.

---

### 🤖 Smart Logic

* 🧠 AI-based priority assignment (keyword-driven).

* 🚨 Emergency override (URGENT delivers in bad signal).

* ⏱ Delivery prediction system.

---

### 🗺 Simulation

* 🚗 Trip simulation (A → B movement).

* 📍 Geo-based signal zones.

* 📡 Coverage-based decision making.

---

## 🧱 Tech Stack

### Backend

* **FastAPI** (API + WebSocket).

* **SQLite** (database).

* **Python asyncio** (background worker).

* **JWT/Auth (API key based)**.

### Frontend

* HTML + CSS + JS Dashboard.

* Real-time updates via WebSocket.

* Interactive UI (queue, logs, analytics).

---

## 🏗 Architecture

```

User/UI → FastAPI → Queue → Decision Engine → Delivery Engine

↓

Signal Engine

↓

WebSocket Broadcast → UI

```

---

## 🔄 How It Works

1. **User sends notification**.

* API: `/notifications`.

2. **Backend assigns priority**.

* Manual OR AI-based.

3. **Checks current signal**.

* GREEN / YELLOW / RED.

4. **Decision Engine**.

* Deliver OR Defer.

5. **Retry system**.

* Exponential backoff.

6. **WebSocket updates UI**.

* Live logs + queue updates.

---

## 📡 Signal Logic

Priority | Allowed Signal     |

| -------- | ------------------ |

| URGENT    GREEN, YELLOW, RED |

| HIGH     | GREEN, YELLOW      |

| NORMAL   | GREEN              |

| LOW      | GREEN              |

---

## ▶️ How to Run

### 1️⃣ Install dependencies

```bash

pip install fastapi uvicorn

```

---

### 2️⃣ Start server

```bash

python -m server:app --reload

```

---

### 3️⃣ Open UI

```

http://127.0.0.1:8000

```

---

## 🔑 API Authentication

Use API key:

```bash

Authorization: Bearer Team201A

```

---

## 📡 Important APIs

### ➤ Create Notification

```

POST /notifications

```

---

### ➤ Update Location

```http

POST /location

```

---

### ➤ Simulate Trip

```http

POST /trip/simulate

```

---

### ➤ Get Analytics

```http

GET /analytics

```

---

## 🔌 WebSocket Events

| Event                  | Description            |

| ---------------------- | ---------------------- |

| notification_created   | notification       |

| notification_delivered | Delivered              |

| notification_deferred  | Waiting for signal     |

| notification_retrying  | Retry attempt          |

notification_failed    | Failed after retries   |

| position_update        | Signal/location change |

---

## 🎯 Use Cases

* 🚗 Smart vehicle alerts.

* 🚑 Emergency systems.

* 📡 Rural network optimization.

* 📲 Battery-efficient notifications.

* 🛰 Telecom infrastructure simulation.

---

## 🧠 Key Concepts Used

* Priority Queues.

* Event-driven Architecture.

* WebSockets.

* Retry Mechanisms.

* Geo-based Decision Systems.

* Real-time UI sync.

---

## 🏆 Why This Project Stands Out

* Not just CRUD. **System-level thinking**.

* Real-world problem (network + delivery).

* stack + real-time integration.

* Simulation +. Logic.

---

## 🚀 Future Improvements

* 📱 Mobile app (Flutter/React Native).

*, 🤖 ML-based delivery prediction.

* 📊 Advanced analytics dashboard.

* 🌍 Real map integration (Google Maps API).

---

## 👨‍💻 Team

* Built as a *hackathon-level intelligent system**.

* Focus: backend systems + real-time architecture.

---

## 🧠 One-Line Summary

> **“A smart notification system that decides the time to deliver messages based on network conditions and priority.”**
<img width="1920" height="1080" alt="Screenshot (40)" src="https://github.com/user-attachments/assets/9c57570d-d3c7-4d66-82d6-14a20db191c5" />
<img width="1920" height="1080" alt="Screenshot (44)" src="https://github.com/user-attachments/assets/14bf4308-1696-45a4-a042-cf28245a72f4" />
<img width="1920" height="1080" alt="Screenshot (43)" src="https://github.com/user-attachments/assets/5b21f436-b11c-4f8c-a6a6-2eb617543f8a" />
<img width="1920" height="1080" alt="Screenshot (42)" src="https://github.com/user-attachments/assets/14f01201-7005-4257-9701-6056c8b6ec72" />
<img width="1920" height="1080" alt="Screenshot (41)" src="https://github.com/user-attachments/assets/2c6a9256-fa60-43d6-a730-efa02b23a967" />
