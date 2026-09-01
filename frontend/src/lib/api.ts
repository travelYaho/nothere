import { API_BASE_URL } from "./supabase";

export type HomeResponse = {
  user: { id: string; nickname: string };
  draftSchedule: {
    scheduleId: string;
    title: string;
    travelDate: string | null;
    status: string;
  } | null;
  recentSchedules: {
    scheduleId: string;
    title: string;
    travelDate: string | null;
    status: string;
  }[];
};

export type UserResponse = {
  id: string;
  email: string;
  nickname: string;
  profileImageUrl: string | null;
};

async function apiFetch<T>(
  path: string,
  accessToken: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.message ?? `요청 실패 (${response.status})`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function fetchHome(accessToken: string) {
  return apiFetch<HomeResponse>("/api/home", accessToken);
}

export function fetchMe(accessToken: string) {
  return apiFetch<UserResponse>("/api/users/me", accessToken);
}

export function signup(payload: {
  email: string;
  password: string;
  nickname: string;
}) {
  return fetch(`${API_BASE_URL}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then(async (response) => {
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.message ?? `회원가입 실패 (${response.status})`);
    }
    return body;
  });
}
