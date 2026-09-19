import { api } from "./client";
import type { CalendarRead, DashboardRead } from "./types";

export const dashboardApi = {
  get: () => api.get<DashboardRead>("/dashboard"),
  calendar: (year?: number, month?: number) =>
    api.get<CalendarRead>("/calendar", { query: { year, month } }),
};
