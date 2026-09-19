import { api } from "./client";
import type {
  ContentActionResponse,
  ContentAssetRole,
  ContentFormat,
  ContentObjective,
  ContentRead,
  ContentStatus,
  ContentSummary,
  ContentVersionRead,
  CreationQuestion,
  JobAccepted,
  Page,
  RegenerationScope,
  VisualTone,
} from "./types";

export const contentsApi = {
  generate: (payload: {
    product_id?: string | null;
    service_id?: string | null;
    objective: ContentObjective;
    format?: ContentFormat | null;
    answers?: Record<string, string>;
    planned_date?: string | null;
    visual_tone?: VisualTone;
  }) => api.post<JobAccepted>("/contents/generate", payload),

  generateQuestions: (params: {
    objective: ContentObjective;
    product_id?: string | null;
    service_id?: string | null;
  }) =>
    api.get<CreationQuestion[]>("/contents/generate/questions", {
      query: {
        objective: params.objective,
        product_id: params.product_id,
        service_id: params.service_id,
      },
    }),

  createFromIdea: (payload: {
    idea_id: string;
    format?: ContentFormat | null;
    instruction?: string | null;
    planned_date?: string | null;
  }) => api.post<JobAccepted>("/contents/from-idea", payload),

  createManual: (payload: {
    title: string;
    format: ContentFormat;
    category?: string | null;
    concept?: string | null;
    objective?: string | null;
    caption?: string | null;
    cta?: string | null;
    hashtags?: string[];
    planned_date?: string | null;
  }) => api.post<ContentRead>("/contents", payload),

  list: (filters?: {
    status?: ContentStatus[];
    format?: ContentFormat[];
    category?: string;
    search?: string;
    plannedFrom?: string;
    plannedTo?: string;
    limit?: number;
    offset?: number;
  }) =>
    api.get<Page<ContentSummary>>("/contents", {
      query: {
        status: filters?.status,
        format: filters?.format,
        category: filters?.category,
        search: filters?.search,
        planned_from: filters?.plannedFrom,
        planned_to: filters?.plannedTo,
        limit: filters?.limit,
        offset: filters?.offset,
      },
    }),

  get: (id: string) => api.get<ContentRead>(`/contents/${id}`),

  versions: (id: string) => api.get<ContentVersionRead[]>(`/contents/${id}/versions`),

  update: (
    id: string,
    payload: Partial<{
      title: string;
      concept: string | null;
      objective: string | null;
      category: string | null;
      caption: string | null;
      cta: string | null;
      hashtags: string[];
      planned_date: string | null;
      payload: Record<string, unknown>;
      change_reason: string | null;
    }>
  ) => api.patch<ContentRead>(`/contents/${id}`, payload),

  regenerate: (
    id: string,
    payload: { scope: RegenerationScope; instruction?: string | null }
  ) => api.post<JobAccepted>(`/contents/${id}/regenerate`, payload),

  changeFormat: (
    id: string,
    payload: { format: ContentFormat; regenerate?: boolean; instruction?: string | null }
  ) => api.post<ContentActionResponse>(`/contents/${id}/change-format`, payload),

  duplicate: (id: string, title?: string | null) =>
    api.post<ContentRead>(`/contents/${id}/duplicate`, { title }),

  restoreVersion: (id: string, version: number) =>
    api.post<ContentRead>(`/contents/${id}/versions/${version}/restore`),

  changeStatus: (
    id: string,
    payload: { status: ContentStatus; planned_date?: string | null; reason?: string | null }
  ) => api.post<ContentRead>(`/contents/${id}/status`, payload),

  approve: (id: string) => api.post<ContentRead>(`/contents/${id}/approve`),
  reject: (id: string) => api.post<ContentRead>(`/contents/${id}/reject`),
  archive: (id: string) => api.post<ContentRead>(`/contents/${id}/archive`),

  schedule: (id: string, plannedDate: string) =>
    api.post<ContentRead>(`/contents/${id}/schedule`, { planned_date: plannedDate }),

  remove: (id: string) => api.delete<{ message: string }>(`/contents/${id}`),

  linkAsset: (id: string, payload: { asset_id: string; role?: ContentAssetRole; position?: number }) =>
    api.post<ContentRead>(`/contents/${id}/assets`, payload),

  unlinkAsset: (id: string, assetId: string) =>
    api.delete<ContentRead>(`/contents/${id}/assets/${assetId}`),
};
