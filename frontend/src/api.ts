export interface LanguageInfo {
  code: string;
  name: string;
  tts_voice: string;
}

export interface Phoneme {
  ipa: string;
  status: "native" | "foreign";
  display: string;
  substitute: string | null;
  minor: boolean;
  stress: number;
}

export interface Chunk {
  text: string;
  status: "native" | "foreign";
  stressed: boolean;
  word_index: number;
  phonemes: Phoneme[];
}

export interface MissingSound {
  ipa: string;
  substitute: string;
  substitute_display: string;
  minor: boolean;
  distance: number;
}

export interface AnalyzeResult {
  text: string;
  query: string;
  input_lang: string;
  native: { code: string; name: string };
  target: { code: string; name: string };
  translated: string | null;
  approximation: string;
  chunks: Chunk[];
  missing_sounds: MissingSound[];
  expected_ipa: string[];
}

export type VerdictStatus = "correct" | "close" | "wrong" | "missing";

export interface Verdict {
  expected: string;
  recognized: string | null;
  status: VerdictStatus;
  distance: number;
  hint: string;
  foreign: boolean;
}

export interface AssessResult {
  recognized_ipa: string[];
  score: number;
  verdicts: Verdict[];
  extra_sounds?: string[];
  message?: string;
}

export interface Drill {
  sound: string;
  description: string;
  how_to: string;
  native_note: string;
  examples: { word: string; ipa: string }[];
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function fetchLanguages(): Promise<LanguageInfo[]> {
  const res = await fetch("/api/languages");
  return jsonOrThrow<LanguageInfo[]>(res);
}

export async function analyze(
  native: string,
  target: string,
  text: string,
  inputLang: "target" | "native" = "target"
): Promise<AnalyzeResult> {
  const res = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ native, target, text, input_lang: inputLang }),
  });
  return jsonOrThrow<AnalyzeResult>(res);
}

export async function assess(
  audio: Blob,
  expectedIpa: string[],
  native: string,
  target: string
): Promise<AssessResult> {
  const form = new FormData();
  form.append("audio", audio, "recording.webm");
  form.append("expected_ipa", expectedIpa.join(" "));
  form.append("native", native);
  form.append("target", target);
  const res = await fetch("/api/assess", { method: "POST", body: form });
  return jsonOrThrow<AssessResult>(res);
}

export async function tts(text: string, target: string): Promise<string> {
  const res = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ native: target, target, text }),
  });
  if (!res.ok) throw new Error("TTS failed");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function fetchDrill(
  sound: string,
  target: string,
  native: string
): Promise<Drill> {
  const params = new URLSearchParams({ sound, target, native });
  const res = await fetch(`/api/drill?${params}`);
  return jsonOrThrow<Drill>(res);
}
