import { api } from "./client";
import type { BusinessCreatePayload, BusinessRead, BusinessUpdatePayload } from "./types";

export const businessApi = {
  create: (payload: BusinessCreatePayload) => api.post<BusinessRead>("/business", payload),
  list: () => api.get<BusinessRead[]>("/business"),
  current: () => api.get<BusinessRead>("/business/current"),
  updateCurrent: (payload: BusinessUpdatePayload) =>
    api.patch<BusinessRead>("/business/current", payload),
  remove: (businessId: string) =>
    api.delete<{ message: string }>(`/business/${businessId}`),
};
