import { Badge } from "@/components/ui/badge";
import type { ContentStatus, IdeaStatus, JobStatus } from "@/lib/api/types";

const CONTENT_STATUS_META: Record<ContentStatus, { label: string; tone: "neutral" | "brand" | "success" | "warning" | "danger" | "info" }> = {
  IDEA: { label: "Ideia", tone: "neutral" },
  DRAFT: { label: "Rascunho", tone: "info" },
  REVIEW: { label: "Em revisao", tone: "warning" },
  APPROVED: { label: "Aprovado", tone: "success" },
  SCHEDULED: { label: "Agendado", tone: "brand" },
  PUBLISHED: { label: "Publicado", tone: "success" },
  REJECTED: { label: "Rejeitado", tone: "danger" },
  ARCHIVED: { label: "Arquivado", tone: "neutral" },
};

export function ContentStatusBadge({ status }: { status: ContentStatus }) {
  const meta = CONTENT_STATUS_META[status];
  return <Badge tone={meta.tone}>{meta.label}</Badge>;
}

const IDEA_STATUS_META: Record<IdeaStatus, { label: string; tone: "neutral" | "success" | "danger" }> = {
  AVAILABLE: { label: "Disponivel", tone: "success" },
  USED: { label: "Usada", tone: "neutral" },
  DISCARDED: { label: "Descartada", tone: "danger" },
};

export function IdeaStatusBadge({ status }: { status: IdeaStatus }) {
  const meta = IDEA_STATUS_META[status];
  return <Badge tone={meta.tone}>{meta.label}</Badge>;
}

const JOB_STATUS_META: Record<JobStatus, { label: string; tone: "neutral" | "success" | "danger" | "warning" }> = {
  PENDING: { label: "Na fila", tone: "neutral" },
  PROCESSING: { label: "Processando", tone: "warning" },
  COMPLETED: { label: "Concluido", tone: "success" },
  FAILED: { label: "Falhou", tone: "danger" },
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  const meta = JOB_STATUS_META[status];
  return <Badge tone={meta.tone}>{meta.label}</Badge>;
}
