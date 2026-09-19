import { api } from "./client";
import type { AICapabilitiesRead, FormatRead, TaxonomyRead } from "./types";

export const aiApi = {
  taxonomy: () => api.get<TaxonomyRead>("/ai/taxonomy"),
  formats: () => api.get<FormatRead[]>("/ai/formats"),
  capabilities: () => api.get<AICapabilitiesRead>("/ai/capabilities"),
};
