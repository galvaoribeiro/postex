import { api } from "./client";
import type { ProductPayload, ProductRead, ServicePayload, ServiceRead } from "./types";

export const productsApi = {
  list: (onlyActive = false) =>
    api.get<ProductRead[]>("/products", { query: { only_active: onlyActive } }),
  create: (payload: ProductPayload) => api.post<ProductRead>("/products", payload),
  update: (id: string, payload: Partial<ProductPayload>) =>
    api.patch<ProductRead>(`/products/${id}`, payload),
  remove: (id: string) => api.delete<{ message: string }>(`/products/${id}`),
};

export const servicesApi = {
  list: (onlyActive = false) =>
    api.get<ServiceRead[]>("/services", { query: { only_active: onlyActive } }),
  create: (payload: ServicePayload) => api.post<ServiceRead>("/services", payload),
  update: (id: string, payload: Partial<ServicePayload>) =>
    api.patch<ServiceRead>(`/services/${id}`, payload),
  remove: (id: string) => api.delete<{ message: string }>(`/services/${id}`),
};
