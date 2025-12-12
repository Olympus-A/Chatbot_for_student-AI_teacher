# AI Student Tutor Chatbot

AI-powered tutor that lets students chat with a helpful assistant. The Next.js frontend talks to a FastAPI backend that stores conversation history in MongoDB and generates replies with OpenAI.

## Features
- Conversational UI with persistent session IDs per tab
- FastAPI endpoints for chat and conversation history
- MongoDB storage for prompts and message history
- OpenAI-powered responses with configurable system prompt

## Tech Stack
- Frontend: Next.js 14, React 18, Tailwind CSS, Axios, Lucide icons
- Backend: FastAPI, OpenAI Python SDK, Motor (MongoDB async driver)
- Database: MongoDB

## Prerequisites
- Node.js 18+
- Python 3.10+
- MongoDB instance
- OpenAI API key

## Setup

### 1) Backend (FastAPI)
```bash
cd server
python -m venv .venv
. .venv/Scripts/activate    # on Windows
pip install -r requirements.txt
```

Create a `.env` file in `server/`:
```
OPENAI_API_KEY=your_openai_api_key
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=ai_chatbot
```

Seed the system prompt (required). In MongoDB, create a document in `chat_prompt` collection with `name: "chat_prompt"` and a `prompt` string. Example using `mongosh`:
```js
use ai_chatbot
db.chat_prompt.insertOne({
  name: "chat_prompt",
  prompt: "You are a helpful AI tutor for students. Keep answers clear and concise."
})
```

Run the API:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend (Next.js)
```bash
cd client
npm install
```

Create `client/.env.local` (optional if using defaults):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the dev server:
```bash
npm run dev
# app at http://localhost:3000
```

## Usage
1. Start MongoDB and the FastAPI server.
2. Start the Next.js dev server.
3. Open `http://localhost:3000`, ask a question, and get AI tutor responses.

Each browser tab gets a unique session ID so conversation context persists as you chat.

## API Overview
- `GET /` — health check.
- `POST /chat` — send `{ message, session_id? }`; returns `{ response, session_id }` and stores history.
- `GET /conversations/{session_id}` — fetch recent messages.
- `POST /conversations/new` — start a new conversation.
- `DELETE /conversations/{session_id}` — delete a conversation.

## Project Structure
- `client/` — Next.js UI (`src/app/page.tsx` main chat interface).
- `server/` — FastAPI service (`main.py` routes, `database.py` Mongo helper, `schema.py` models).

## Notes
- CORS is configured for `http://localhost:3000` by default; adjust in `server/main.py` if needed.
- If the backend cannot reach OpenAI, the frontend shows a friendly error message.

Completed Fix

