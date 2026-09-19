import { api } from "./client";
import type { JobKind, JobRead, JobStatus } from "./types";

export const jobsApi = {
  get: (id: string) => api.get<JobRead>(`/jobs/${id}`),
  list: (filters?: { kind?: JobKind; status?: JobStatus; limit?: number }) =>
    api.get<JobRead[]>("/jobs", {
      query: { kind: filters?.kind, status: filters?.status, limit: filters?.limit },
    }),
};

const TERMINAL_STATUSES: JobStatus[] = ["COMPLETED", "FAILED"];

/** Faz polling de um job ate ele terminar (COMPLETED ou FAILED). */
export async function waitForJob(
  jobId: string,
  options?: { intervalMs?: number; timeoutMs?: number; signal?: AbortSignal }
): Promise<JobRead> {
  const intervalMs = options?.intervalMs ?? 1200;
  const timeoutMs = options?.timeoutMs ?? 120_000;
  const start = Date.now();

  while (true) {
    const job = await jobsApi.get(jobId);
    if (TERMINAL_STATUSES.includes(job.status)) return job;
    if (Date.now() - start > timeoutMs) {
      throw new Error("O processamento esta demorando mais que o esperado.");
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
    if (options?.signal?.aborted) {
      throw new DOMException("Aborted", "AbortError");
    }
  }
}
