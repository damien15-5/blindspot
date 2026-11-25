export type Prediction = { id: number; label: string; score: number };
export type Trial = {
  id: string;
  artifact_sha: string;
  condition: string;
  level: number;
  image: string;
  outcome: string;
  predictions: Prediction[];
  mass: number;
  cached: number;
  duration_ms: number;
};
export type Photo = {
  id: string;
  title: string;
  source_id: string;
  source_version: string;
  sha256: string;
  provenance: string;
  state: string;
  accepted: { id: number; label: string }[];
  trials: Trial[];
  recall: {
    id: string;
    score: number;
    metadata: { condition: string; trial: string };
  }[];
};
export type Run = {
  id: string;
  goal: string;
  model_sha: string;
  preprocessing_sha: string;
  model_revision: string;
  state: string;
  seed: number;
  cursor: number;
  budget: number;
  inference_cpu_ms: number;
  pending_writes: number;
  photos: Photo[];
  decisions: {
    photo_id: string;
    action: string;
    reason_code: string;
    evidence_ids: string[];
    budget_remaining: number;
  }[];
  events: {
    provider: string;
    method: string;
    path: string;
    status: string;
    duration_ms: number;
  }[];
};
export type Api = <T>(path: string, options?: RequestInit) => Promise<T>;
export const post = (body?: unknown): RequestInit => ({
  method: "POST",
  ...(body === undefined
    ? {}
    : {
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
});
