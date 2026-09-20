import { api } from "./client";
import type { JobAccepted } from "./types";

export const talentsApi = {
  generate: () => api.post<JobAccepted>("/talents/generate"),
};
