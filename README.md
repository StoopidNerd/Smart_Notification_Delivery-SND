# Geo-Deferred Notification System

## Overview

The Geo-Deferred Notification System is a way to send notifications when the network is good. It does not send messages away. Instead it waits until the network is better to send -urgent messages.

## Problem Statement

Old notification systems have some problems:

* They fail to deliver messages in areas with network

* They try times and waste data

* They disturb users when they are busy with something

## Solution

Our system is smart and knows when the network is good or bad:

* Important messages are sent right away

* Important messages are sent when the network is better

* The system sends messages automatically when the network improves

## Tech Stack

* We use Python and Flask for the backend

* We use SQLite for the database

* We use REST APIs to communicate

## Features

* The system is smart about when to send messages

* It prioritizes messages based on importance

* It knows when the network is good or bad

* It tries again when the network is better

* It stores messages in a database

## API Endpoints

### 1. Send Notification

```http

POST /send

```

**Headers:**

```text

x-api-key: Team201A

```

****

```json

{

"message": " fuel"

"priority": "LOW"

}

```

### 2. Update Network

```http

POST /network

```

```json

{

"strength": 80

}

```

### 3. Get Notifications

```http

GET /notifications

```

## How to Run

First you need to install Flask:

```bash

pip install flask

```

Then you can run the server:

```bash

python server.py

```

The server will run on:

```text

http://127.0.0.1:5000

```

## Team Collaboration

* The backend runs on the computer

* Team members can access it using the IP:

```text

http://<your-ip>:5000

```

* Make sure all devices are on the same network

## Future Improvements

* We can make the system detect the network in time

* We can add a frontend dashboard to visualize the data

* We can use AI to prioritize messages

* We can deploy it on the cloud

## Team

* You are the backend developer

* Team members are the frontend developers

##

This project shows a way to handle notifications when the network is poor. It makes the system more reliable uses data and improves the user experience. The Geo-Deferred Notification System is a solution, for connected mobility systems.<img width="1920" height="1080" alt="Screenshot (40)" src="https://github.com/user-attachments/assets/9c57570d-d3c7-4d66-82d6-14a20db191c5" />
<img width="1920" height="1080" alt="Screenshot (44)" src="https://github.com/user-attachments/assets/14bf4308-1696-45a4-a042-cf28245a72f4" />
<img width="1920" height="1080" alt="Screenshot (43)" src="https://github.com/user-attachments/assets/5b21f436-b11c-4f8c-a6a6-2eb617543f8a" />
<img width="1920" height="1080" alt="Screenshot (42)" src="https://github.com/user-attachments/assets/14f01201-7005-4257-9701-6056c8b6ec72" />
<img width="1920" height="1080" alt="Screenshot (41)" src="https://github.com/user-attachments/assets/2c6a9256-fa60-43d6-a730-efa02b23a967" />
