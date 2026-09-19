import { api } from "./client";
import type {
  ContentFormat,
  ContentIdeaRead,
  IdeaStatus,
  JobAccepted,
} from "./types";

export const ideasApi = {
  generate: (payload: {
    count?: number;
    categories?: string[];
    format_hint?: ContentFormat | null;
    instruction?: string | null;
  }) => api.post<JobAccepted>("/content-ideas/generate", payload),
  list: (filters?: {
    status?: IdeaStatus;
    category?: string;
    format?: ContentFormat;
    limit?: number;
    offset?: number;
  }) =>
    api.get<ContentIdeaRead[]>("/content-ideas", {
      query: {
        status: filters?.status,
        category: filters?.category,
        format: filters?.format,
        limit: filters?.limit,
        offset: filters?.offset,
      },
    }),
  get: (id: string) => api.get<ContentIdeaRead>(`/content-ideas/${id}`),
  setStatus: (id: string, status: IdeaStatus) =>
    api.patch<ContentIdeaRead>(`/content-ideas/${id}`, { status }),
  remove: (id: string) => api.delete<{ message: string }>(`/content-ideas/${id}`),
};
