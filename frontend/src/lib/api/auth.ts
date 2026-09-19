import { api } from "./client";
import type { SessionResponse, UserRead } from "./types";

export const authApi = {
  register: (payload: { email: string; password: string; full_name: string }) =>
    api.post<SessionResponse>("/auth/register", payload),
  login: (payload: { email: string; password: string }) =>
    api.post<SessionResponse>("/auth/login", payload),
  logout: () => api.post<{ message: string }>("/auth/logout"),
  refresh: () => api.post<SessionResponse>("/auth/refresh"),
  me: () => api.get<SessionResponse>("/auth/me"),
  updateProfile: (payload: { full_name?: string }) => api.patch<UserRead>("/auth/me", payload),
  changePassword: (payload: { current_password: string; new_password: string }) =>
    api.post<{ message: string }>("/auth/change-password", payload),
};
