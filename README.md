# Real-Time Multilingual Lecture Assistant

This project captures lecture audio from a React frontend, streams it to a FastAPI backend, and returns:

- live English transcription
- live translation to Hindi or Tamil
- a rolling simplified explanation
- keyword extraction for quick revision

The current implementation runs transcription, translation, and summarization with local/open models loaded by the backend.

## Stack

- Frontend: React + Vite + Tailwind CSS
- Backend: FastAPI + WebSocket + multipart uploads
- Speech-to-text: `faster-whisper`
- Translation: Hugging Face seq2seq models
- Summarization: extractive summary for fast updates, abstractive summary for uploaded/full text flows

## Project structure

```text
/
|-- backend/
|   |-- main.py
|   |-- requirements.txt
|   |-- .env.example
|   `-- services/
|       |-- speech.py
|       |-- translate.py
|       `-- summarize.py
|-- frontend/
|   |-- package.json
|   |-- src/
|   |   |-- App.jsx
|   |   `-- components/
|   |       |-- Recorder.jsx
|   |       `-- Display.jsx
|   `-- vite.config.js
`-- README.md
```

## Features

- Microphone streaming over WebSocket for near real-time updates
- Audio file upload flow for one-shot processing
- Language switching while a live session is active
- Rolling transcript merge to reduce duplicate chunk output
- Live keyword extraction from the current lecture context
- Health endpoint that reports loaded model/device configuration

## Supported languages

- Source speech: English
- Translation targets:
  - Hindi (`hi`)
  - Tamil (`ta`)

## Prerequisites

- Python 3.10+
- Node.js 18+
- `ffmpeg` available on your system path

Notes:
- The backend may download model weights the first time it runs.
- CPU works, but GPU is strongly recommended for better latency.

## Backend setup

```powershell
cd d:\Projects\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Frontend setup

```powershell
cd d:\Projects\frontend
npm install
```

## Environment variables

Backend settings live in `backend/.env`.

Important defaults from `backend/.env.example`:

```env
WHISPER_MODEL_SIZE=tiny.en
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=int8
TRANSLATION_MODEL_NAME=facebook/m2m100_418M
TRANSLATION_DEVICE=auto
SUMMARY_MODEL_NAME=sshleifer/distilbart-cnn-12-6
SUMMARY_DEVICE=auto
LIVE_SUMMARY_MODE=fast
ENABLE_BACKGROUND_WARMUP=1
MIN_TRANSCRIPT_CHARS=3
```

Frontend optional variables:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

If the frontend variables are not set, the app falls back to `http://localhost:8000` and derives the WebSocket URL from it.

## Run the app

Start the backend:

```powershell
cd d:\Projects\backend
.venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend:

```powershell
cd d:\Projects\frontend
npm run dev
```

Open `http://localhost:5173`.

## How it works

### Live mode

1. The browser records audio in short chunks with `MediaRecorder`.
2. The frontend sends each chunk to `ws://localhost:8000/ws/lecture`.
3. The backend transcribes the audio, translates the newest chunk, rebuilds the simplified summary, and extracts keywords.
4. The frontend updates the transcript, translation, summary, and keyword panels.

### Upload mode

1. The user uploads an audio file from the frontend.
2. The frontend sends it to `POST /upload`.
3. The backend transcribes the full file and returns transcript, translation, summary, and keywords in one response.

## API endpoints

- `GET /health`
  Returns backend status plus selected model/device information.
- `POST /upload`
  Accepts multipart form data with:
  - `file`
  - `target_language`
- `WS /ws/lecture`
  Accepts audio chunks as binary frames and optional JSON control messages such as:

```json
{ "type": "set_language", "target_language": "ta" }
```

## Local testing

1. Start both servers.
2. Open the frontend in the browser.
3. Click `Start Microphone` and allow microphone access.
4. Speak a few English lecture-style sentences.
5. Confirm that transcript, translation, summary, and keywords begin updating.
6. Switch between Hindi and Tamil during the session.
7. Test `Upload Audio File` with a short spoken audio clip.

## Notes and troubleshooting

- First startup can be slower because model weights may need to load or download.
- If live transcription feels slow on CPU, try smaller models or run on a CUDA-enabled machine.
- If uploaded or streamed audio returns empty text, check microphone permissions and confirm `ffmpeg` is installed.
- `LIVE_SUMMARY_MODE=fast` uses extractive summarization for lower latency during live streaming.
- The health endpoint is useful for confirming whether the backend selected `cpu` or `cuda`.
