import { useMemo, useState } from "react";
import Recorder from "./components/Recorder";
import Display from "./components/Display";

const languageOptions = [
  { code: "hi", label: "Hindi" },
  { code: "ta", label: "Tamil" },
];

const emptyPayload = {
  original: "",
  translated: "",
  summary: "Start speaking to generate a simplified explanation.",
  keywords: [],
};

function App() {
  const [targetLanguage, setTargetLanguage] = useState("hi");
  const [viewMode, setViewMode] = useState("split");
  const [feed, setFeed] = useState(emptyPayload);
  const [status, setStatus] = useState("Idle");
  const [error, setError] = useState("");

  const backendHttpUrl = useMemo(
    () => import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
    [],
  );
  const backendWsUrl = useMemo(() => {
    if (import.meta.env.VITE_WS_BASE_URL) {
      return import.meta.env.VITE_WS_BASE_URL;
    }

    const httpUrl = backendHttpUrl.replace(/^http/, "ws");
    return httpUrl;
  }, [backendHttpUrl]);

  const onIncomingPayload = (payload) => {
    setFeed({
      original: payload.original ?? "",
      translated: payload.translated ?? "",
      summary: payload.summary ?? emptyPayload.summary,
      keywords: payload.keywords ?? [],
    });
    setError(payload.error ?? "");
  };

  return (
    <main className="min-h-screen px-4 py-6 text-slate-50 sm:px-6 lg:px-10">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-panel backdrop-blur">
          <p className="mb-3 text-sm font-semibold uppercase tracking-[0.3em] text-aqua">
            Real-Time Multilingual Lecture Assistant
          </p>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <h1 className="text-3xl font-bold tracking-tight text-sand sm:text-5xl">
                Stream a lecture, translate it live, and turn it into quick study notes.
              </h1>
              <p className="mt-3 max-w-2xl text-sm text-slate-200 sm:text-base">
                The frontend streams microphone chunks over WebSocket. The backend transcribes,
                translates, extracts keywords, and keeps a rolling simplified explanation live.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="rounded-2xl border border-white/10 bg-slate-950/50 p-3">
                <span className="mb-2 block text-xs uppercase tracking-[0.25em] text-slate-400">
                  Translate To
                </span>
                <select
                  className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-50 outline-none focus:border-coral"
                  value={targetLanguage}
                  onChange={(event) => setTargetLanguage(event.target.value)}
                >
                  {languageOptions.map((language) => (
                    <option key={language.code} value={language.code}>
                      {language.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="rounded-2xl border border-white/10 bg-slate-950/50 p-3">
                <span className="mb-2 block text-xs uppercase tracking-[0.25em] text-slate-400">
                  View
                </span>
                <select
                  className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-50 outline-none focus:border-coral"
                  value={viewMode}
                  onChange={(event) => setViewMode(event.target.value)}
                >
                  <option value="split">Split</option>
                  <option value="original">Original</option>
                  <option value="translated">Translated</option>
                  <option value="summary">Simplified</option>
                </select>
              </label>
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[380px_1fr]">
          <Recorder
            apiBaseUrl={backendHttpUrl}
            wsBaseUrl={backendWsUrl}
            targetLanguage={targetLanguage}
            onPayload={onIncomingPayload}
            onStatus={setStatus}
            onError={setError}
          />

          <Display
            data={feed}
            error={error}
            status={status}
            targetLanguage={languageOptions.find((item) => item.code === targetLanguage)?.label}
            viewMode={viewMode}
          />
        </section>
      </div>
    </main>
  );
}

export default App;
