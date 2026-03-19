function Panel({ title, content, accent, emptyMessage }) {
  return (
    <section className="rounded-[1.75rem] border border-white/10 bg-slate-950/45 p-5 shadow-panel">
      <p className={`text-xs font-semibold uppercase tracking-[0.3em] ${accent}`}>{title}</p>
      <div className="mt-4 min-h-32 whitespace-pre-wrap text-sm leading-7 text-slate-100 sm:text-base">
        {content || <span className="text-slate-400">{emptyMessage}</span>}
      </div>
    </section>
  );
}

function Display({ data, error, status, targetLanguage, viewMode }) {
  const showOriginal = viewMode === "split" || viewMode === "original";
  const showTranslated = viewMode === "split" || viewMode === "translated";
  const showSummary = viewMode === "split" || viewMode === "summary";

  return (
    <section className="space-y-6">
      <div className="rounded-[2rem] border border-white/10 bg-white/5 p-5 shadow-panel backdrop-blur">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Session</p>
            <h2 className="mt-2 text-2xl font-semibold text-sand">Live classroom feed</h2>
          </div>

          <div className="flex flex-wrap gap-3 text-sm">
            <div className="rounded-full border border-white/10 bg-slate-950/60 px-4 py-2">
              Status: <span className="font-semibold text-aqua">{status}</span>
            </div>
            <div className="rounded-full border border-white/10 bg-slate-950/60 px-4 py-2">
              Target: <span className="font-semibold text-coral">{targetLanguage}</span>
            </div>
            <div className="rounded-full border border-white/10 bg-slate-950/60 px-4 py-2">
              Keywords: <span className="font-semibold text-sand">{data.keywords.length}</span>
            </div>
          </div>
        </div>

        {error ? (
          <div className="mt-4 rounded-2xl border border-red-400/40 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        ) : null}
      </div>

      <div
        className={`grid gap-6 ${
          viewMode === "split" ? "xl:grid-cols-2" : "grid-cols-1"
        }`}
      >
        {showOriginal ? (
          <Panel
            title="Original Transcript"
            accent="text-aqua"
            content={data.original}
            emptyMessage="Your live transcript will appear here."
          />
        ) : null}

        {showTranslated ? (
          <Panel
            title="Translated Output"
            accent="text-coral"
            content={data.translated}
            emptyMessage="The translated lecture will appear here."
          />
        ) : null}

        {showSummary ? (
          <Panel
            title="Simplified Explanation"
            accent="text-sand"
            content={data.summary}
            emptyMessage="A simpler explanation will appear here."
          />
        ) : null}
      </div>

      <div className="rounded-[1.75rem] border border-white/10 bg-slate-950/45 p-5 shadow-panel">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
          Keywords
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          {data.keywords.length ? (
            data.keywords.map((keyword) => (
              <span
                key={keyword}
                className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-100"
              >
                {keyword}
              </span>
            ))
          ) : (
            <span className="text-sm text-slate-400">Keywords will show up after transcription.</span>
          )}
        </div>
      </div>
    </section>
  );
}

export default Display;
