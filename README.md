# WAAA (WhatsApp Auto Alerts)

**Submission for INNOVATE 4 IMPACT: AI4SDG Global Hackathon 2026**  
**Theme:** Smart Technology & Innovation | **Problem Statement:** PS-A02

## Project Overview

WhatsApp is a primary communication tool, but muting or archiving noisy groups can cause users to miss critical, time-sensitive updates. Its built-in features do not provide intelligent prioritization across those conversations.

WAAA is a full-stack automation prototype that connects a React dashboard to a WhatsApp Web session. It caches chats and messages locally, detects priority keywords in muted or archived chats, recovers locally cached text from deleted-message notifications, and streams updates to the dashboard in real time.

## Core Features

- **Priority keyword detection:** Checks incoming messages in muted or archived chats for the built-in keywords `deadline`, `meeting`, `interview`, and `urgent`, then creates a priority alert.
- **Deleted message recovery:** Handles Baileys revoke protocol messages, retrieves the original message text from the local cache when available, marks the message as revoked, and creates a recovery alert.
- **Real-time dashboard:** Streams chats, messages, and alerts between the backend and React frontend using Socket.IO.
- **Persistent local cache:** Stores chats, messages, and alerts in SQLite for local persistence and retrieval.
- **Behavior analysis placeholder:** Provides a REST endpoint ready for a future AI integration. It currently returns a mock suggestion and does not call Gemini.

## Tech Stack

- **Frontend:** React, Vite, Tailwind CSS, Lucide Icons
- **Backend:** Node.js, Express
- **WhatsApp integration:** `@whiskeysockets/baileys`
- **Real-time bridge:** Socket.IO
- **Database:** SQLite using `sqlite` and `sqlite3`

## Local Setup

Requirements: Node.js and npm installed. Run the backend and frontend in separate terminals.

### 1. Clone the repository

```bash
git clone https://github.com/pranavvoidking01-cmyk/EDI-Project-Final.git
cd EDI-Project-Final
```

### 2. Start the backend

```bash
cd backend
npm install
npm start
```

On first run, Baileys prints a QR code in the terminal. In WhatsApp, open **Settings > Linked Devices** and scan it. The session is stored locally so subsequent starts can reuse it.

The backend API and Socket.IO server run at `http://localhost:3000` by default.

### 3. Start the frontend

Open a second terminal in the repository root:

```bash
npm install
npm run dev
```

Open the Vite URL printed in the terminal, usually `http://localhost:5173`.

## API

- `GET /api/status` - backend health check
- `GET /api/chats` - cached chats and latest-message summaries
- `GET /api/alerts` - cached alerts
- `GET /api/messages/:chatId` - latest 100 messages for a chat
- `POST /api/analyze-behavior` - mock behavior suggestion; send `{ "chatId": "..." }`

## Privacy and Security

- Chat and message data is cached in the local `backend/waaa.db` SQLite database.
- WhatsApp authentication files are stored in `backend/auth_info_baileys/`.
- Local databases, authentication files, dependencies, build output, and environment files are excluded from version control.
- The behavior-analysis endpoint is currently a local mock; no message content is sent to Gemini or another third-party AI service.

## Current Prototype Scope

- Priority keywords are currently hard-coded in the backend; user-configurable keywords are a future enhancement.
- Deleted message recovery requires the original message to exist in the local cache and can recover only the content types currently parsed by the prototype.
- The AI behavior-analysis endpoint returns a static suggestion and is not connected to Gemini yet.
- Baileys connects to WhatsApp Web and is not the official WhatsApp Cloud API. Use it in accordance with applicable terms and for development or demonstration purposes.

## Future Work

- Integrate Gemini for behavior analysis and configurable alert suggestions.
- Add user-managed keyword lists and alert settings.
- Explore official WhatsApp Cloud API integration for supported production use cases.
- Add phishing and fraud detection for suspicious links or message patterns.
- Build a mobile companion app for native notifications.
