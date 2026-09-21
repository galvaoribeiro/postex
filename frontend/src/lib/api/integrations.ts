import { api } from "./client";
import type { CampaignDestination, JobAccepted } from "./types";

export const integrationsApi = {
  generate: (payload: {
    product_id: string;
    model_asset_id: string;
    destination: CampaignDestination;
  }) => api.post<JobAccepted>("/integrations/generate", payload),
};
