import api from "./client";

export type CollectConfig = {
  round_label?: string;
  leaf_size_bytes?: number;
  counts?: Record<string, number>;
  beacons?: Record<string, string[]>;
  quotes?: Record<string, any>;
  weather_locations?: any;
  textfeeds?: Record<string, number>;
  images?: string[];
  persist_raw?: boolean;
};

export async function collectAndCommit(config: CollectConfig) {
  const res = await api.post("/sources/collect-and-commit", config);
  return res.data as { round_id: string; manifest: Record<string, any> };
}

export async function postBeacon(roundId: string, payload: { S_hex: string; vdf_T: number; modulus_bits: number }) {
  const res = await api.post(`/rounds/${roundId}/beacon`, payload);
  return res.data;
}

export async function finalizeRound(roundId: string, payload: { output_bits: number }) {
  const res = await api.post(`/rounds/${roundId}/finalize`, payload);
  return res.data as { analysis: any; output_hex: string };
}

export async function generateRange(
  roundId: string,
  body: { start: number; end: number; count: number; domain?: string; context?: string }
) {
  const res = await api.post(`/rounds/${roundId}/random-range`, body);
  return res.data as { numbers: number[]; info: Record<string, any> };
}

export async function fetchOutputText(roundId: string) {
  const res = await api.get(`/rounds/${roundId}/output.txt`, { responseType: "blob" });
  return res.data as Blob;
}

export async function analyzeRound(roundId: string, limitBits?: number) {
  const res = await api.post(`/analysis/round/${roundId}`, { limit_bits: limitBits });
  return res.data;
}

export async function analyzeSequence(payload: any) {
  const res = await api.post("/analysis/sequence", payload);
  return res.data;
}

export async function uploadSequence(file: File, limitBits?: number) {
  const form = new FormData();
  form.append("file", file);
  const res = await api.post(`/analysis/upload${limitBits ? `?limit_bits=${limitBits}` : ""}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function runHeavyTest(roundId: string, args?: string[]) {
  const res = await api.post(`/analysis/round/${roundId}/heavy`, {
    test: "dieharder",
    dieharder_args: args,
  });
  return res.data;
}
