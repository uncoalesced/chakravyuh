// Engineered by uncoalesced
import { useEffect, useRef } from "react";
import { useFeed } from "./useFeed.js";

const STATES = [
  ["PANIC", "Shows fear"],
  ["STALLING", "Buys time"],
  ["BAITING", "Asks for payee"],
  ["EXTRACTING", "Asks for repeats"],
  ["WRAPUP", "Hands off"],
];

const KIND = { upi: "UPI ID", account: "Bank account", ifsc: "IFSC", phone: "Phone", url: "Link", apk: "App link" };

const clock = (s = 0) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

function Badge({ children }) {
  return <span className="badge">{children}</span>;
}

function Header({ connected, call }) {
  return (
    <header className="top">
      <div className="brand">
        <span className="mark" aria-hidden>◎</span>
        <h1>Chakravyuh</h1>
        <span className="sub">Live call</span>
      </div>
      <div className="meta">
        {call?.scenario && <span className="scenario">{call.scenario}</span>}
        {call?.simulated !== false && call && <Badge>SIMULATED</Badge>}
        <span className={`conn ${connected ? "on" : ""}`}>{connected ? "Connected" : "Connecting…"}</span>
      </div>
    </header>
  );
}

function Stepper({ state }) {
  const at = STATES.findIndex(([s]) => s === state);
  return (
    <ol className="stepper" aria-label="Persona state">
      {STATES.map(([s, hint], i) => (
        <li key={s} className={i === at ? "now" : i < at ? "done" : ""} aria-current={i === at ? "step" : undefined}>
          <span className="dot" />
          <span className="name">{s}</span>
          <span className="hint">{hint}</span>
        </li>
      ))}
    </ol>
  );
}

function Transcript({ messages, call }) {
  const end = useRef(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages.length]);
  return (
    <section className="card transcript">
      <h2>Conversation</h2>
      {!call && <p className="empty">Waiting for a call…</p>}
      <div className="msgs">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.speaker}`}>
            <div className="who">
              {m.speaker === "scammer" ? "Caller" : "Persona"}
              {m.state && <span className={`pill s-${m.state}`}>{m.state}</span>}
              {m.cut && <span className="pill cut">interrupted</span>}
              {m.ts != null && <span className="ts">{clock(m.ts)}</span>}
            </div>
            <p>{m.text}</p>
          </div>
        ))}
        <div ref={end} />
      </div>
    </section>
  );
}

function Counter({ metrics, report }) {
  const secs = metrics?.engaged_s ?? report?.metrics?.engaged_seconds ?? 0;
  const cost = metrics?.illustrative_cost_inr ?? report?.metrics?.illustrative_cost_inr ?? 0;
  return (
    <section className="card counter">
      <div className="row">
        <h2>Caller time spent</h2>
        <Badge>SIMULATED</Badge>
      </div>
      <div className="big">{clock(secs)}</div>
      <div className="cost">
        ₹{cost.toFixed(2)} <span>illustrative cost to the caller, at an assumed rate</span>
      </div>
    </section>
  );
}

function Intel({ intel }) {
  return (
    <section className="card intel">
      <div className="row">
        <h2>Captured details</h2>
        <span className="count">{intel.length}</span>
      </div>
      {intel.length === 0 && <p className="empty">Nothing yet. Payment details appear here as the caller reads them out.</p>}
      <ul>
        {intel.map((i) => (
          <li key={`${i.kind}:${i.value}`}>
            <div className="k">{KIND[i.kind] ?? i.kind}<span className="ts">{clock(i.ts)}</span></div>
            <code>{i.value}</code>
            <span className={`fmt ${i.valid ? "ok" : "unk"}`}>{i.valid ? "Format valid" : "Format unrecognised"}</span>
            {i.note && <span className="note">{i.note}</span>}
          </li>
        ))}
      </ul>
      <p className="fine">Format checks only. Nothing here is verified or confirmed as fraudulent.</p>
    </section>
  );
}

function Report({ report }) {
  if (!report) return null;
  const download = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: `chakravyuh-report-${Date.now()}.json` });
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <section className="card report">
      <div>
        <h2>Report ready for review</h2>
        <p>
          {report.intel?.length ?? 0} details, {report.call?.turns ?? 0} turns. Prepared for a person to review and submit
          through the official channels (cybercrime.gov.in, helpline 1930, Chakshu on Sanchar Saathi).
        </p>
      </div>
      <button onClick={download}>Download JSON</button>
    </section>
  );
}

export default function App() {
  const feed = useFeed();
  return (
    <div className="app">
      <Header connected={feed.connected} call={feed.call} />
      <Stepper state={feed.state} />
      <main>
        <Transcript messages={feed.messages} call={feed.call} />
        <aside>
          <Counter metrics={feed.metrics} report={feed.report} />
          <Intel intel={feed.intel} />
        </aside>
      </main>
      <Report report={feed.report} />
    </div>
  );
}
