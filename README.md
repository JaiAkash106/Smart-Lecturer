# Real-Time Multilingual Lecture Assistant

A complete MVP that streams microphone audio from a React frontend to a FastAPI backend, transcribes it with OpenAI Whisper, translates it to Hindi or Tamil, and shows a rolling simplified explanation plus keywords in the UI.

## Project structure

```text
/backend
  main.py
  requirements.txt
  .env.example
  services/
    speech.py
    translate.py
    summarize.py
/frontend
  package.json
  index.html
  src/
    App.jsx
    components/
      Recorder.jsx
      Display.jsx
```

## Install

### Backend

```powershell
cd d:\Projects\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Set `OPENAI_API_KEY` in `backend/.env`.

### Frontend

```powershell
cd d:\Projects\frontend
npm install
```

## Run

### Start the backend

```powershell
cd d:\Projects\backend
.venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Start the frontend

```powershell
cd d:\Projects\frontend
npm run dev
```

Open `http://localhost:5173`.

## How it works

1. The browser records microphone audio in short `MediaRecorder` chunks.
2. The frontend sends each chunk to `ws://localhost:8000/ws/lecture`.
3. FastAPI saves the chunk, transcribes it with OpenAI, translates it, refreshes the summary, extracts keywords, and sends JSON back to the browser.
4. The UI updates the original transcript, translated text, simplified explanation, and keyword pills live.

## Local testing

1. Start both servers.
2. Click `Start Microphone`.
3. Speak a few lecture-style sentences in English.
4. Watch the transcript and translation update every few seconds.
5. Switch the view selector to `Translated` or `Simplified`.
6. Test the bonus flow with `Upload Audio File`.

## Notes

- Live transcription needs an `OPENAI_API_KEY`.
- Translation uses `deep-translator` with Google Translate under the hood, so internet access is needed at runtime.
- The simplified explanation and keywords are generated locally for speed and lower cost.
