// ── Typed API Client ─────────────────────────────────────────────────
// Replaces bare fetch() + localStorage token handling scattered across index.html

// For User App, base is empty; for Admin App, base is /admin
const IS_USER_APP = window.location.hash.includes("/app") || window.location.pathname.startsWith("/app");
const BASE = IS_USER_APP ? "" : "/admin";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function getToken(): string {
  return (
    localStorage.getItem("admin_token") ||
    localStorage.getItem("mos_admin_token") ||
    ""
  );
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  if (!token) return { "Content-Type": "application/json" };
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.status === 401) {
    const wasToken = !!getToken();
    localStorage.removeItem("admin_token");
    localStorage.removeItem("mos_admin_token");
    if (wasToken) {
      window.location.reload();
    }
    throw new ApiError(401, "Session expired");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async get<T>(path: string): Promise<T> {
    const res = await fetch(`${BASE}${path}`, { headers: authHeaders() });
    return handleResponse<T>(res);
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: authHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(res);
  },

  async put<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
      method: "PUT",
      headers: authHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(res);
  },
};
