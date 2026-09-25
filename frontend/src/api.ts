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

// ---- accounts / SRS -------------------------------------------------------

export interface User {
  id: number;
  username: string;
  email: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type Rating = "again" | "hard" | "good" | "easy";

export interface Confidence {
  percent: number;
  label: string;
}

export interface SrsState {
  state: "new" | "learning" | "review";
  ease: number;
  interval_days: number;
  reps: number;
  lapses: number;
  due_at: string | null;
  last_review_at: string | null;
  confidence: Confidence;
  due: boolean;
  next_intervals: Record<Rating, string>;
}

export interface SavedWord {
  id: number;
  text: string;
  translated: string | null;
  approximation: string;
  expected_ipa: string[];
  native: string;
  target: string;
  missing_sounds: MissingSound[];
  created_at: string;
  srs: SrsState;
  pronunciation?: PronunciationFeedback;
}

// ---- pronunciation feedback -----------------------------------------------

export interface PronunciationSuggestionInfo {
  id: number;
  text: string;
  up: number;
  down: number;
  rate: number;
  my_vote: "up" | "down" | null;
  mine: boolean;
  in_audience: boolean;
  promoted: boolean;
}

export interface PronunciationFeedback {
  native: string;
  target: string;
  text: string;
  system: { up: number; down: number; my_vote: "up" | "down" | null };
  suggestions: PronunciationSuggestionInfo[];
  effective: {
    source: "system" | "suggestion";
    text: string | null;
    suggestion_id: number | null;
  };
}

export type PronunciationVote = "up" | "down";

export interface PracticeQueue {
  items: SavedWord[];
  counts: { due: number; new: number };
  next_due: string | null;
}

export interface Progress {
  total: number;
  new: number;
  learning: number;
  review: number;
  mastered: number;
  due_now: number;
  streak: number;
  reviews_last_30d: { date: string; count: number }[];
  forecast: { date: string; count: number }[];
}

// ---- fetch helpers --------------------------------------------------------

const TOKEN_KEY = "spiik_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// a protected endpoint rejected our token — drop it and go log in again
function handleExpired(res: Response): void {
  if (res.status === 401 && getToken()) {
    setToken(null);
    window.location.href = "/login";
  }
}

// FastAPI validation errors send detail as an array of { msg, loc, ... }
// instead of the plain string other handlers use.
function detailText(detail: unknown): string {
  const parts = (Array.isArray(detail) ? detail : [detail]).map((d) =>
    d && typeof d === "object" && "msg" in d
      ? String((d as { msg: unknown }).msg)
      : String(d)
  );
  return parts.filter(Boolean).join("; ") || "Request failed";
}

async function errorFrom(res: Response): Promise<Error> {
  let detail: unknown = res.statusText;
  try {
    const body = await res.json();
    if (body.detail) detail = body.detail;
  } catch {
    /* keep statusText */
  }
  return new Error(detailText(detail));
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) throw await errorFrom(res);
  return res.json() as Promise<T>;
}

async function authJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { ...authHeaders(), ...init?.headers },
  });
  handleExpired(res);
  return jsonOrThrow<T>(res);
}

// ---- phonetics endpoints --------------------------------------------------

export interface HealthInfo {
  status: string;
  version: string;
  engine: string;
}

export async function fetchHealth(): Promise<HealthInfo> {
  const res = await fetch("/api/health");
  return jsonOrThrow<HealthInfo>(res);
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

// ---- auth endpoints -------------------------------------------------------

export async function register(
  username: string,
  email: string,
  password: string
): Promise<AuthResponse> {
  const res = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password }),
  });
  return jsonOrThrow<AuthResponse>(res);
}

export async function login(
  username: string,
  password: string
): Promise<AuthResponse> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  return jsonOrThrow<AuthResponse>(res);
}

export async function fetchMe(): Promise<User> {
  return authJson<User>("/api/auth/me");
}

export async function updateProfile(
  fields: { username?: string; email?: string }
): Promise<User> {
  return authJson<User>("/api/auth/me", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
}

export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<void> {
  const res = await fetch("/api/auth/password", {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  if (!res.ok) throw await errorFrom(res);
}

// ---- saved words / practice / progress ------------------------------------

export async function saveWord(
  text: string,
  native: string,
  target: string,
  translated: string | null = null
): Promise<SavedWord> {
  // text is the practice word shown on the trainer card (target language);
  // the meaning the user saw travels in `translated`
  return authJson<SavedWord>("/api/words", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, native, target, translated }),
  });
}

export async function fetchWords(): Promise<SavedWord[]> {
  return authJson<SavedWord[]>("/api/words");
}

export async function deleteWord(id: number): Promise<void> {
  const res = await fetch(`/api/words/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  handleExpired(res);
  if (!res.ok) throw await errorFrom(res);
}

export async function fetchPractice(): Promise<PracticeQueue> {
  return authJson<PracticeQueue>("/api/practice");
}

export async function reviewWord(
  id: number,
  rating: Rating
): Promise<SavedWord> {
  return authJson<SavedWord>(`/api/practice/${id}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating }),
  });
}

export async function fetchProgress(): Promise<Progress> {
  return authJson<Progress>("/api/progress");
}

// ---- pronunciation feedback ------------------------------------------------

export async function fetchPronunciationFeedback(
  native: string,
  target: string,
  text: string
): Promise<PronunciationFeedback> {
  const params = new URLSearchParams({ native, target, text });
  return authJson<PronunciationFeedback>(`/api/pronunciation/feedback?${params}`);
}

export async function votePronunciation(
  native: string,
  target: string,
  text: string,
  suggestionId: number | null,
  vote: PronunciationVote
): Promise<PronunciationFeedback> {
  return authJson<PronunciationFeedback>("/api/pronunciation/vote", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      native,
      target,
      text,
      suggestion_id: suggestionId,
      vote,
    }),
  });
}

export async function suggestPronunciation(
  native: string,
  target: string,
  text: string,
  suggestedText: string
): Promise<PronunciationFeedback> {
  return authJson<PronunciationFeedback>("/api/pronunciation/suggest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ native, target, text, suggested_text: suggestedText }),
  });
}
