"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";

import { waitForJob } from "@/lib/api/jobs";
import type { JobRead } from "@/lib/api/types";

const KIND_LABELS: Record<string, string> = {
  IDEATION: "Geracao de ideias",
  CONTENT_PRODUCTION: "Producao de conteudo",
  CONTENT_REGENERATION: "Regeneracao de conteudo",
  ASSET_ANALYSIS: "Analise de imagem",
};

interface WatchOptions {
  loadingMessage?: string;
  successMessage?: string | ((job: JobRead) => string);
  onSuccess?: (job: JobRead) => void | Promise<void>;
  onError?: (message: string) => void;
}

/**
 * Acompanha um job de IA ate o fim, mostrando toasts de progresso.
 * Operacoes de IA respondem 202 com um `job_id`; esse hook centraliza o
 * polling para nao repetir a logica em cada tela.
 */
export function useJobWatcher() {
  const [isWatching, setIsWatching] = useState(false);

  const watch = useCallback(async (jobId: string, kind: string, options?: WatchOptions) => {
    setIsWatching(true);
    const label = KIND_LABELS[kind] ?? "Processamento";
    const toastId = toast.loading(options?.loadingMessage ?? `${label} em andamento...`);

    try {
      const job = await waitForJob(jobId);
      if (job.status === "COMPLETED") {
        const message =
          typeof options?.successMessage === "function"
            ? options.successMessage(job)
            : options?.successMessage ?? `${label} concluida.`;
        toast.success(message, { id: toastId });
        await options?.onSuccess?.(job);
      } else {
        const message = job.error_message ?? `${label} falhou.`;
        toast.error(message, { id: toastId });
        options?.onError?.(message);
      }
      return job;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Falha inesperada.";
      toast.error(message, { id: toastId });
      options?.onError?.(message);
      return null;
    } finally {
      setIsWatching(false);
    }
  }, []);

  return { watch, isWatching };
}
