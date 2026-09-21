import { api } from "./client";
import type {
  CampaignDestination,
  CampaignGenerateAccepted,
  CampaignOutput,
  CampaignRead,
  CampaignStatus,
  CampaignSummary,
  CreationQuestion,
  DestinationRead,
  Page,
} from "./types";

export const campaignsApi = {
  destinations: () => api.get<DestinationRead[]>("/campaigns/destinations"),

  generateQuestions: (params: { product_id: string; destination: CampaignDestination }) =>
    api.get<CreationQuestion[]>("/campaigns/generate/questions", {
      query: {
        product_id: params.product_id,
        destination: params.destination,
      },
    }),

  generate: (payload: {
    product_id: string;
    model_asset_id: string;
    destination: CampaignDestination;
    outputs?: CampaignOutput[] | null;
    answers?: Record<string, string>;
    cover_asset_id?: string | null;
  }) => api.post<CampaignGenerateAccepted>("/campaigns/generate", payload),

  list: (filters?: {
    status?: CampaignStatus[];
    destination?: CampaignDestination[];
    productId?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) =>
    api.get<Page<CampaignSummary>>("/campaigns", {
      query: {
        status: filters?.status,
        destination: filters?.destination,
        product_id: filters?.productId,
        search: filters?.search,
        limit: filters?.limit,
        offset: filters?.offset,
      },
    }),

  get: (id: string) => api.get<CampaignRead>(`/campaigns/${id}`),

  regenerate: (id: string, payload: { output: CampaignOutput; instruction?: string | null }) =>
    api.post<CampaignGenerateAccepted>(`/campaigns/${id}/regenerate`, payload),

  approve: (id: string) => api.post<CampaignRead>(`/campaigns/${id}/approve`),

  changeStatus: (id: string, payload: { status: CampaignStatus; reason?: string | null }) =>
    api.post<CampaignRead>(`/campaigns/${id}/status`, payload),
};
