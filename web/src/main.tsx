import React, { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Owner } from "./Owner";
import { post, type Run, type Trial, type Api } from "./types";
import "./style.css";

const pct = (v: number) => (100 * v).toFixed(1) + "%";
const short = (s: string) => s.split(",")[0];
function Mark() {
  return (
    <svg viewBox="0 0 40 40" width="36" height="36" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M4 15V6h9m14 0h9v9M4 25v9h9m14 0h9v-9" />
        <circle cx="20" cy="20" r="8" />
      </g>
      <circle fill="currentColor" cx="20" cy="20" r="3" />
    </svg>
  );
}
function Frame({
  t,
  variant,
  token,
}: {
  t: Trial;
  variant: boolean;
  token: string;
}) {
  const [url, setUrl] = useState(""),
    [err, setErr] = useState(false);
  useEffect(() => {
    setErr(false);
    setUrl("");
    if (t.image.startsWith("/demo/")) return;
    let active = true,
      object = "";
    fetch(t.image, { headers: { Authorization: "Bearer " + token } })
      .then(async (r) => {
        if (!r.ok) throw Error();
        object = URL.createObjectURL(await r.blob());
        if (active) setUrl(object);
        else URL.revokeObjectURL(object);
      })
      .catch(() => {
        if (active) setErr(true);
      });
    return () => {
      active = false;
      if (object) URL.revokeObjectURL(object);
    };
  }, [t.image, token]);
  const src = t.image.startsWith("/demo/") ? t.image : url;
  return (
    <article className={"frame " + (variant ? "variant" : "")}>
      <div className="framehead">
        <span className="mono">
          <i />
          {variant ? "GENERATED VARIANT" : "ORIGINAL"}
        </span>
        <span>{variant ? "Level " + t.level : "Baseline"}</span>
      </div>
      <div className="photo">
        {src ? (
          <img
            src={src}
            alt={
              (variant ? t.condition + " variant" : "Original") +
              " of the selected object"
            }
          />
        ) : err ? (
          "Image unavailable"
        ) : (
          "Loading image…"
        )}
      </div>
      <div className="pred">
        <div className="cap">TOP FIVE PREDICTIONS</div>
        {t.predictions.map((p, i) => (
          <div className={"bar b" + i} key={p.id} title={p.label}>
            <div style={{ width: pct(p.score) }} />
            <span>{short(p.label)}</span>
            <b>{pct(p.score)}</b>
          </div>
        ))}
      </div>
    </article>
  );
}
function App() {
  const [token, setToken] = useState(""),
    [entry, setEntry] = useState(""),
    [owner, setOwner] = useState(false),
    [mode, setMode] = useState("demo"),
    [box, setBox] = useState(false),
    [unlock, setUnlock] = useState(false),
    [view, setView] = useState("followup"),
    [run, setRun] = useState<Run | null>(null),
    [ownRun, setOwnRun] = useState<Run | null>(null),
    [pi, setPi] = useState(0),
    [ti, setTi] = useState(0),
    [error, setError] = useState("");
  const api: Api = useCallback(
    async (path, opts = {}) => {
      const r = await fetch(path, {
        ...opts,
        headers: {
          ...opts.headers,
          ...(token ? { Authorization: "Bearer " + token } : {}),
        },
      });
      if (!r.ok) {
        const body = await r.json();
        throw Error(
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail),
        );
      }
      return r.json();
    },
    [token],
  );
  useEffect(() => {
    api<{ owner: boolean; mode: string; box: boolean }>("/api/status")
      .then((s) => {
        setOwner(s.owner);
        setMode(s.mode);
        setBox(s.box);
        if (token && !s.owner) setError("Owner token was declined");
        if (s.owner) {
          setUnlock(false);
          setError("");
        }
      })
      .catch((e) => setError(e.message));
  }, [api, token]);
  useEffect(() => {
    let active = true;
    if (view === "owner") {
      setRun(ownRun);
      return;
    }
    api<Run>("/demo/" + view + ".json")
      .then((r) => {
        if (active) {
          setRun(r);
          const n = r.photos.findIndex((p) => p.trials.length > 1);
          setPi(Math.max(0, n));
          setTi(r.photos[Math.max(0, n)].trials.length - 1);
        }
      })
      .catch((e) => setError(e.message));
    return () => {
      active = false;
    };
  }, [view, api, ownRun]);
  function load(r: Run) {
    setOwnRun(r);
    setView("owner");
    const i = Math.max(
      0,
      r.photos.map((p) => p.trials.length > 0).lastIndexOf(true),
    );
    setPi(i);
    setTi(Math.max(0, r.photos[i].trials.length - 1));
  }
  async function download(toBox: boolean) {
    if (!ownRun) return;
    const opts = post({
      run_id: ownRun.id,
      destination: toBox ? "box" : "local",
    });
    const r = await fetch("/api/export", {
      ...opts,
      headers: { ...opts.headers, Authorization: "Bearer " + token },
    });
    if (!r.ok) throw Error((await r.json()).detail);
    if (toBox) {
      setError("Exported Box file " + (await r.json()).box_file_id);
      return;
    }
    const href = URL.createObjectURL(await r.blob());
    const a = document.createElement("a");
    a.href = href;
    a.download = "BlindSpot-report.html";
    a.click();
    setTimeout(() => URL.revokeObjectURL(href), 1000);
  }
  const photo = run?.photos[pi],
    base = photo?.trials[0],
    tr = photo?.trials[ti] ?? base,
    decisions = run?.decisions.filter((d) => d.photo_id === photo?.id) ?? [],
    change = decisions.find((d) => d.reason_code === "RECALLED_FAILURE"),
    hit = photo?.recall.find((h) => change?.evidence_ids.includes(h.id));
  return (
    <>
      <header>
        <div className="brand">
          <Mark />
          BlindSpot
        </div>
        <span className="headtag">Vision test bench</span>
        <div className="headright">
          <span className="dot" /> CPU runtime{" "}
          {mode === "owner" && !owner && (
            <button onClick={() => setUnlock(!unlock)}>Owner access</button>
          )}
        </div>
      </header>
      <div className="shell">
        <aside>
          <div className="cap">WORKSPACE</div>
          <div className="sideTitle">Experiment log</div>
          {[
            ["session", "Sample collection", "12 objects"],
            ["followup", "Follow-up session", "1 object"],
          ].map(([key, name, n]) => (
            <button
              className={"nav " + (view === key ? "selected" : "")}
              key={key}
              onClick={() => setView(key)}
            >
              <strong>{name}</strong>
              <small>{n} · saved run</small>
            </button>
          ))}
          {owner && (
            <button
              className={"nav " + (view === "owner" ? "selected" : "")}
              onClick={() => setView("owner")}
            >
              Owner workspace
            </button>
          )}
          <div className="sidefoot">
            <div className="cap">CLASSIFIER</div>MobileNetV4 Small
            <small>Quantized ONNX · ImageNet-1K</small>
          </div>
        </aside>
        <main>
          {unlock && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setToken(entry);
                setEntry("");
              }}
            >
              <label>
                Owner token
                <input
                  type="password"
                  value={entry}
                  onChange={(e) => setEntry(e.target.value)}
                />
              </label>
              <button>Unlock</button>
            </form>
          )}
          {error && <p role="status">{error}</p>}
          <div className="eyebrow">
            <span className="dot" />
            {view === "owner" ? "OWNER WORKSPACE" : "SAMPLE / SAVED EXPERIMENT"}
          </div>
          <h1>
            {view === "followup"
              ? "Follow-up session"
              : view === "session"
                ? "Sample collection"
                : "Owner workspace"}
          </h1>
          <p className="sub">
            {view === "owner"
              ? (run?.goal ?? "Import a labelled photo to start a run.")
              : "Camera-condition trials on labelled collection photographs."}
          </p>
          {owner && view === "owner" && (
            <Owner
              api={api}
              run={ownRun}
              load={load}
              box={box}
              download={download}
            />
          )}
          {run && photo && (
            <>
              <div className="metrics">
                <div>
                  <small>Run state</small>
                  <b>{run.state === "done" ? "Complete" : "Active"}</b>
                </div>
                <div>
                  <small>Camera trials</small>
                  <b>
                    {run.photos.reduce(
                      (s, p) => s + Math.max(0, p.trials.length - 1),
                      0,
                    )}
                  </b>
                </div>
                <div>
                  <small>Inference CPU</small>
                  <b>
                    {run.inference_cpu_ms.toFixed(1)} <em>ms</em>
                  </b>
                </div>
                <div>
                  <small>Failure memory</small>
                  <b className="compact">
                    {run.events.find(
                      (e) =>
                        e.provider === "LOCAL/MOCK" ||
                        e.provider === "pinecone",
                    )?.provider ?? "No calls"}
                  </b>
                </div>
              </div>
              <section>
                <div className="sectitle">
                  <h2>Image comparison</h2>
                  <select
                    aria-label="Photo"
                    value={pi}
                    onChange={(e) => {
                      setPi(+e.target.value);
                      setTi(
                        Math.max(
                          0,
                          run.photos[+e.target.value].trials.length - 1,
                        ),
                      );
                    }}
                  >
                    {run.photos.map((p, i) => (
                      <option key={p.id} value={i}>
                        {p.title} · {p.source_version}
                      </option>
                    ))}
                  </select>
                </div>
                <p className="meta">
                  {photo.provenance} <span>/</span> Accepted class ·{" "}
                  {photo.accepted.map((a) => short(a.label)).join(", ") ||
                    "Awaiting label"}
                </p>
                {base && tr ? (
                  <>
                    <div className="tabs">
                      {photo.trials.map((t, i) => (
                        <button
                          aria-pressed={i === ti}
                          key={t.id}
                          onClick={() => setTi(i)}
                        >
                          {t.level ? t.condition + " · " + t.level : "Original"}
                        </button>
                      ))}
                    </div>
                    <div className="pair">
                      <Frame t={base} variant={false} token={token} />
                      {tr.level > 0 && <Frame t={tr} variant token={token} />}
                    </div>
                    <p
                      className={
                        "outcome " + (tr.outcome === "accepted" ? "ok" : "")
                      }
                    >
                      <b>{tr.outcome}</b>{" "}
                      {tr.level
                        ? short(base.predictions[0].label) +
                          " → " +
                          short(tr.predictions[0].label)
                        : "Original top prediction compared with the accepted class."}
                    </p>
                  </>
                ) : (
                  <p>Awaiting the next owner step.</p>
                )}
              </section>
              <div className="detailsgrid">
                <section>
                  <h2>Decision timeline</h2>
                  <ol className="timeline">
                    {decisions.map((d, i) => (
                      <li key={i}>
                        <b>{d.action.replaceAll("_", " ")}</b>
                        <div>{d.reason_code}</div>
                        <small>{d.budget_remaining} variants left</small>
                      </li>
                    ))}
                  </ol>
                </section>
                <div>
                  <section>
                    <h2>Failure memory</h2>
                    <p>
                      {hit
                        ? "Recalled a " +
                          hit.metadata.condition +
                          " failure. The agent moved it ahead of blur."
                        : decisions.some(
                              (d) =>
                                d.reason_code === "REMOTE_MEMORY_UNAVAILABLE",
                            )
                          ? "Remote memory unavailable. The agent used the default test order."
                          : photo.recall.length
                            ? "Similar cases retrieved. The default first test kept its place."
                            : "No prior case changed the test order."}
                    </p>
                    {hit && (
                      <small className="hash">
                        Cosine {hit.score.toFixed(3)} · case {hit.id}
                      </small>
                    )}
                  </section>
                  <section>
                    <h2>Connector trace</h2>
                    {run.pending_writes > 0 && (
                      <p role="status">
                        {run.pending_writes} memory write(s) pending owner
                        retry.
                      </p>
                    )}
                    {run.events.length ? (
                      run.events.map((e, i) => (
                        <div className="trace" key={i}>
                          <b>
                            {e.provider} · {e.method}
                          </b>
                          <small>
                            {e.path} · {e.status} · {e.duration_ms.toFixed(2)}{" "}
                            ms
                          </small>
                        </div>
                      ))
                    ) : (
                      <p>No connector calls recorded.</p>
                    )}
                  </section>
                </div>
              </div>
              <section>
                <div className="sectitle">
                  <h2>Run report</h2>
                  <a
                    download={"BlindSpot-" + view + ".json"}
                    href={
                      "data:application/json;charset=utf-8," +
                      encodeURIComponent(JSON.stringify(run, null, 2))
                    }
                  >
                    Download JSON ↓
                  </a>
                </div>
                <dl>
                  {[
                    ["Model SHA-256", run.model_sha],
                    ["Preprocessing SHA-256", run.preprocessing_sha],
                    ["Photo SHA-256", photo.sha256],
                    ["Deterministic seed", run.seed],
                  ].map(([k, v]) => (
                    <React.Fragment key={k}>
                      <dt>{k}</dt>
                      <dd>{v}</dd>
                    </React.Fragment>
                  ))}
                </dl>
              </section>
            </>
          )}
        </main>
      </div>
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
