import { useEffect, useState } from "react";
import type { Api, Run } from "./types";
import { post } from "./types";

type Library = {
  photos: { id: string; title: string; accepted: string; provenance: string }[];
  runs: { id: string; state: string; goal: string }[];
};
export function Owner({
  api,
  run,
  load,
  box,
  download,
}: {
  api: Api;
  run: Run | null;
  load: (r: Run) => void;
  box: boolean;
  download: (box: boolean) => Promise<void>;
}) {
  const [lib, setLib] = useState<Library>({ photos: [], runs: [] }),
    [ids, select] = useState<string[]>([]),
    [file, setFile] = useState<File | null>(null),
    [label, setLabel] = useState(""),
    [classes, setClasses] = useState<Record<string, string>>({}),
    [goal, setGoal] = useState(
      "Find camera conditions that change my inventory labels",
    ),
    [budget, setBudget] = useState(72),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const refresh = async () => setLib(await api("/api/library"));
  useEffect(() => {
    Promise.all([
      refresh(),
      api<Record<string, string>>("/api/classes").then(setClasses),
    ]).catch((e) => setError(e.message));
  }, [api]);
  const work = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  const add = async (path: string) => {
    const next = await api<string[]>(path, post());
    select(next);
  };
  const classIDs = () =>
    label.trim()
      ? label.split(",").map((v) => {
          const m = v.trim().match(/^(\d+)(?:\s|$)/);
          if (!m || !classes[m[1]])
            throw Error("Choose a class ID from the vocabulary");
          return Number(m[1]);
        })
      : [];
  const step = async () => {
    if (run)
      load(
        await api<Run>(
          "/api/runs/" + run.id + "/step",
          post({ cursor: run.cursor }),
        ),
      );
  };
  return (
    <details className="owner" open={!run}>
      <summary>Owner controls</summary>
      <fieldset disabled={busy}>
        <div className="actions">
          <button onClick={() => work(() => add("/api/samples"))}>
            Load 12 samples
          </button>
          <button onClick={() => work(() => add("/api/samples?held_out=true"))}>
            Load follow-up
          </button>
          {box && (
            <button onClick={() => work(() => add("/api/box/import"))}>
              Import Box folder
            </button>
          )}
        </div>
        <label>
          Photo{" "}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <label>
          Accepted ImageNet class IDs
          <input
            list="classes"
            placeholder="Search by name or enter IDs"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
        </label>
        <datalist id="classes">
          {Object.entries(classes).map(([k, v]) => (
            <option key={k} value={k + " " + v} />
          ))}
        </datalist>
        <button
          disabled={!file}
          onClick={() =>
            work(async () => {
              if (!file) return;
              const form = new FormData();
              form.append("file", file);
              form.append("accepted", JSON.stringify(classIDs()));
              const res = await api<{ id: string }>("/api/import", {
                method: "POST",
                body: form,
              });
              select([res.id]);
            })
          }
        >
          Import photo
        </button>
        <label>
          Run photos · select up to 12
          <select
            multiple
            value={ids}
            onChange={(e) =>
              select(Array.from(e.target.selectedOptions, (o) => o.value))
            }
          >
            {lib.photos.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title} · {p.id.slice(0, 6)} · {p.accepted}
              </option>
            ))}
          </select>
        </label>
        <button
          disabled={ids.length !== 1}
          onClick={() =>
            work(async () => {
              await api(
                "/api/photos/" + ids[0] + "/label",
                post({ accepted: classIDs() }),
              );
              if (run) load(await api("/api/runs/" + run.id));
            })
          }
        >
          Save label for selected photo
        </button>
        <label>
          Goal
          <input value={goal} onChange={(e) => setGoal(e.target.value)} />
        </label>
        <label>
          Variant budget
          <input
            type="number"
            min="1"
            max="72"
            value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
          />
        </label>
        <div className="actions">
          <button
            disabled={!ids.length || ids.length > 12}
            onClick={() =>
              work(async () => {
                const r = await api<{ id: string }>(
                  "/api/runs",
                  post({ photos: ids, goal, budget }),
                );
                load(await api("/api/runs/" + r.id));
              })
            }
          >
            Create run
          </button>
          <button
            disabled={!run || run.state !== "active"}
            onClick={() => work(step)}
          >
            Run next step
          </button>
          <button
            disabled={!run || run.state !== "active"}
            onClick={() =>
              work(async () => {
                if (run)
                  load(
                    await api<Run>(
                      "/api/runs/" + run.id + "/continue",
                      post({ cursor: run.cursor }),
                    ),
                  );
              })
            }
          >
            Continue experiment
          </button>
        </div>
        <label>
          Resume or inspect a run
          <select
            value={run?.id ?? ""}
            onChange={(e) =>
              work(async () => load(await api("/api/runs/" + e.target.value)))
            }
          >
            <option disabled value="">
              Select a run
            </option>
            {lib.runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.id.slice(0, 8)} · {r.state}
              </option>
            ))}
          </select>
        </label>
        {run && (
          <div className="actions">
            <button onClick={() => work(() => download(false))}>
              Export HTML
            </button>
            {box && (
              <button onClick={() => work(() => download(true))}>
                Export to Box
              </button>
            )}
            {run.pending_writes > 0 && (
              <button
                onClick={() =>
                  work(async () =>
                    load(await api("/api/runs/" + run.id + "/retry", post())),
                  )
                }
              >
                Retry pending memory write
              </button>
            )}
          </div>
        )}
      </fieldset>
      {error && <p role="alert">{error}</p>}
    </details>
  );
}
