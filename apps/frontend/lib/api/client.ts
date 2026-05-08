const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:18000/api/v1";
const DEV_USER_ID = process.env.NEXT_PUBLIC_DEV_USER_ID ?? "";

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(DEV_USER_ID ? { "X-User-Id": DEV_USER_ID } : {}),
    ...(init?.headers as Record<string, string>),
  };
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}
