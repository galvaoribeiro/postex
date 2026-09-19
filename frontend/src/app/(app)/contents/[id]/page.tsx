"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Calendar,
  Check,
  Copy,
  History,
  Image as ImageIcon,
  Plus,
  RefreshCw,
  Trash2,
  X,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { FormatBadge } from "@/components/domain/format-badge";
import { PayloadEditor } from "@/components/domain/payload-editor";
import { ContentStatusBadge } from "@/components/domain/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Dialog } from "@/components/ui/dialog";
import { FieldHint, Input, Label, Textarea } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { Select } from "@/components/ui/select";
import { TagInput } from "@/components/ui/tag-input";
import { assetsApi } from "@/lib/api/assets";
import { ApiError } from "@/lib/api/client";
import { contentsApi } from "@/lib/api/contents";
import type { ContentFormat, ContentRead, ContentStatus, RegenerationScope } from "@/lib/api/types";
import { useJobWatcher } from "@/lib/hooks/use-job-watcher";
import { queryKeys } from "@/lib/query-keys";
import { formatDate, formatDateTime } from "@/lib/utils";

const STATUS_LABELS: Record<ContentStatus, string> = {
  IDEA: "Ideia",
  DRAFT: "Rascunho",
  REVIEW: "Enviar para revisao",
  APPROVED: "Aprovar",
  SCHEDULED: "Agendar",
  PUBLISHED: "Marcar como publicado",
  REJECTED: "Rejeitar",
  ARCHIVED: "Arquivar",
};

const SCOPE_LABELS: Record<RegenerationScope, string> = {
  FULL: "Tudo",
  TITLE: "Titulo",
  CONCEPT: "Conceito e objetivo",
  HOOK: "Gancho",
  BODY: "Estrutura do formato",
  CAPTION: "Legenda",
  HASHTAGS: "Hashtags",
  CTA: "Chamada para acao",
};

export default function ContentEditorPage() {
  const params = useParams<{ id: string }>();
  const contentId = params.id;

  const { data: content, isLoading } = useQuery({
    queryKey: queryKeys.content(contentId),
    queryFn: () => contentsApi.get(contentId),
  });

  if (isLoading || !content) {
    return <PageSpinner label="Carregando conteudo..." />;
  }

  // Remonta o formulario quando o conteudo muda de verdade (apos salvar,
  // regenerar, restaurar versao etc.), sincronizando o estado local sem
  // precisar de um efeito com setState.
  return <ContentEditor key={content.updated_at} content={content} contentId={contentId} />;
}

function ContentEditor({ content, contentId }: { content: ContentRead; contentId: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { watch } = useJobWatcher();

  const [title, setTitle] = useState(content.title);
  const [category, setCategory] = useState(content.category ?? "");
  const [concept, setConcept] = useState(content.concept ?? "");
  const [objective, setObjective] = useState(content.objective ?? "");
  const [caption, setCaption] = useState(content.caption ?? "");
  const [cta, setCta] = useState(content.cta ?? "");
  const [hashtags, setHashtags] = useState<string[]>(content.hashtags);
  const [plannedDate, setPlannedDate] = useState(content.planned_date ?? "");
  const [payload, setPayload] = useState<Record<string, unknown>>(content.payload ?? {});

  const [regenerateOpen, setRegenerateOpen] = useState(false);
  const [changeFormatOpen, setChangeFormatOpen] = useState(false);
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [assetPickerOpen, setAssetPickerOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const saveMutation = useMutation({
    mutationFn: () =>
      contentsApi.update(contentId, {
        title,
        category: category || null,
        concept: concept || null,
        objective: objective || null,
        caption: caption || null,
        cta: cta || null,
        hashtags,
        planned_date: plannedDate || null,
        payload,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.content(contentId), updated);
      queryClient.invalidateQueries({ queryKey: ["contents"] });
      toast.success("Alteracoes salvas.");
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        toast.error(error.message, { description: describeValidationErrors(error) });
      } else {
        toast.error("Nao foi possivel salvar.");
      }
    },
  });

  const statusMutation = useMutation({
    mutationFn: (status: ContentStatus) => contentsApi.changeStatus(contentId, { status }),
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.content(contentId), updated);
      queryClient.invalidateQueries({ queryKey: ["contents"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
      toast.success(`Status atualizado para ${STATUS_LABELS[updated.status]}.`);
    },
    onError: (error: unknown) => toast.error(error instanceof ApiError ? error.message : "Erro ao mudar status."),
  });

  const duplicateMutation = useMutation({
    mutationFn: () => contentsApi.duplicate(contentId),
    onSuccess: (copy) => {
      toast.success("Conteudo duplicado.");
      router.push(`/contents/${copy.id}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => contentsApi.remove(contentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contents"] });
      toast.success("Conteudo excluido.");
      router.push("/contents");
    },
  });

  const unlinkAssetMutation = useMutation({
    mutationFn: (assetId: string) => contentsApi.unlinkAsset(contentId, assetId),
    onSuccess: (updated) => queryClient.setQueryData(queryKeys.content(contentId), updated),
  });

  const isDirty =
    title !== content.title ||
    category !== (content.category ?? "") ||
    concept !== (content.concept ?? "") ||
    objective !== (content.objective ?? "") ||
    caption !== (content.caption ?? "") ||
    cta !== (content.cta ?? "") ||
    plannedDate !== (content.planned_date ?? "") ||
    JSON.stringify(hashtags) !== JSON.stringify(content.hashtags) ||
    JSON.stringify(payload) !== JSON.stringify(content.payload);

  return (
    <div className="pb-16">
      <Link href="/contents" className="mb-4 inline-flex items-center gap-1.5 text-sm text-foreground/55 hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Voltar para conteudos
      </Link>

      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div className="flex-1">
          <div className="mb-2 flex items-center gap-2">
            <FormatBadge format={content.format} />
            <ContentStatusBadge status={content.status} />
            <Badge tone="neutral">v{content.current_version}</Badge>
          </div>
          <Input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="h-auto border-none px-0 text-2xl font-semibold shadow-none focus:ring-0"
          />
          <p className="mt-1 text-xs text-foreground/45">
            Criado em {formatDate(content.created_at)} - atualizado em {formatDateTime(content.updated_at)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" icon={<History className="h-4 w-4" />} onClick={() => setVersionsOpen(true)}>
            Versoes
          </Button>
          <Button variant="outline" size="sm" icon={<Copy className="h-4 w-4" />} onClick={() => duplicateMutation.mutate()} loading={duplicateMutation.isPending}>
            Duplicar
          </Button>
          <Button variant="outline" size="sm" onClick={() => setChangeFormatOpen(true)}>
            Trocar formato
          </Button>
          <Button variant="outline" size="sm" icon={<RefreshCw className="h-4 w-4" />} onClick={() => setRegenerateOpen(true)}>
            Regenerar
          </Button>
          <Button variant="ghost" size="icon" onClick={() => setDeleteOpen(true)} aria-label="Excluir">
            <Trash2 className="h-4 w-4 text-danger-fg" />
          </Button>
        </div>
      </div>

      {content.allowed_transitions.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2 rounded-2xl border border-border-subtle bg-surface-muted/50 p-3">
          <span className="self-center text-xs font-medium text-foreground/50">Acoes:</span>
          {content.allowed_transitions.map((status) => (
            <Button
              key={status}
              size="sm"
              variant={status === "APPROVED" ? "primary" : status === "REJECTED" || status === "ARCHIVED" ? "danger" : "outline"}
              onClick={() => statusMutation.mutate(status)}
              loading={statusMutation.isPending && statusMutation.variables === status}
            >
              {STATUS_LABELS[status]}
            </Button>
          ))}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Conceito</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Categoria / pilar</Label>
                <Input value={category} onChange={(event) => setCategory(event.target.value)} />
              </div>
              <div>
                <Label>Conceito</Label>
                <Textarea rows={2} value={concept} onChange={(event) => setConcept(event.target.value)} />
              </div>
              <div>
                <Label>Objetivo</Label>
                <Textarea rows={2} value={objective} onChange={(event) => setObjective(event.target.value)} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Estrutura do {FORMAT_LABEL[content.format]}</CardTitle>
            </CardHeader>
            <CardContent>
              <PayloadEditor format={content.format} payload={payload} onChange={setPayload} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Legenda e publicacao</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Legenda</Label>
                <Textarea rows={4} value={caption} onChange={(event) => setCaption(event.target.value)} />
              </div>
              <div>
                <Label>Chamada para acao (CTA)</Label>
                <Input value={cta} onChange={(event) => setCta(event.target.value)} />
              </div>
              <div>
                <Label>Hashtags</Label>
                <TagInput value={hashtags} onChange={setHashtags} placeholder="Adicionar hashtag" maxItems={30} />
              </div>
            </CardContent>
          </Card>

          <div className="sticky bottom-4 flex justify-end">
            <Button size="lg" onClick={() => saveMutation.mutate()} loading={saveMutation.isPending} disabled={!isDirty}>
              Salvar alteracoes
            </Button>
          </div>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-brand-600" /> Agendamento
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input type="date" value={plannedDate} onChange={(event) => setPlannedDate(event.target.value)} />
              <FieldHint>Salve as alteracoes para confirmar a data planejada.</FieldHint>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ImageIcon className="h-4 w-4 text-brand-600" /> Imagens vinculadas
              </CardTitle>
              <Button size="icon" variant="ghost" onClick={() => setAssetPickerOpen(true)} aria-label="Adicionar imagem">
                <Plus className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>
              {content.assets.length === 0 ? (
                <p className="rounded-xl bg-surface-muted px-3 py-6 text-center text-sm text-foreground/45">
                  Nenhuma imagem vinculada.
                </p>
              ) : (
                <div className="grid grid-cols-2 gap-2">
                  {content.assets.map((link) => (
                    <div key={link.asset.id} className="group relative aspect-square overflow-hidden rounded-lg bg-surface-muted">
                      {link.asset.url && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={link.asset.url} alt={link.asset.alt_text ?? ""} className="h-full w-full object-cover" />
                      )}
                      <button
                        onClick={() => unlinkAssetMutation.mutate(link.asset.id)}
                        className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-black/50 text-white opacity-0 transition-opacity group-hover:opacity-100"
                        aria-label="Desvincular"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                      <span className="absolute bottom-1 left-1 rounded bg-black/50 px-1.5 py-0.5 text-[10px] text-white">
                        {link.role}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <RegenerateDialog
        open={regenerateOpen}
        onClose={() => setRegenerateOpen(false)}
        content={content}
        onWatch={(jobId) =>
          watch(jobId, "CONTENT_REGENERATION", {
            loadingMessage: "Regenerando conteudo...",
            onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.content(contentId) }),
          })
        }
      />

      <ChangeFormatDialog
        key={changeFormatOpen ? "open" : "closed"}
        open={changeFormatOpen}
        onClose={() => setChangeFormatOpen(false)}
        content={content}
        onWatch={(jobId) =>
          watch(jobId, "CONTENT_REGENERATION", {
            loadingMessage: "Reescrevendo no novo formato...",
            onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.content(contentId) }),
          })
        }
        onComplete={(updated) => queryClient.setQueryData(queryKeys.content(contentId), updated)}
      />

      <VersionsDialog
        open={versionsOpen}
        onClose={() => setVersionsOpen(false)}
        contentId={contentId}
        onRestored={(updated) => {
          queryClient.setQueryData(queryKeys.content(contentId), updated);
          setVersionsOpen(false);
        }}
      />

      <AssetPickerDialog
        open={assetPickerOpen}
        onClose={() => setAssetPickerOpen(false)}
        excludeIds={content.assets.map((a) => a.asset.id)}
        onPick={async (assetId) => {
          const updated = await contentsApi.linkAsset(contentId, { asset_id: assetId });
          queryClient.setQueryData(queryKeys.content(contentId), updated);
          setAssetPickerOpen(false);
        }}
      />

      <ConfirmDialog
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        onConfirm={() => deleteMutation.mutate()}
        title="Excluir conteudo"
        description="Essa acao remove o conteudo e todo o seu historico de versoes. Nao pode ser desfeita."
        confirmLabel="Excluir"
        danger
        loading={deleteMutation.isPending}
      />
    </div>
  );
}

const FORMAT_LABEL: Record<ContentFormat, string> = {
  REEL: "Reel",
  IMAGE_POST: "Post",
  CAROUSEL: "Carrossel",
  STORY: "Story",
};

function describeValidationErrors(error: ApiError): string | undefined {
  const errors = error.details?.errors as { loc?: string[]; msg?: string }[] | undefined;
  if (!errors?.length) return undefined;
  return errors.map((item) => `${item.loc?.join(".") ?? ""}: ${item.msg}`).join(" | ");
}

function RegenerateDialog({
  open,
  onClose,
  content,
  onWatch,
}: {
  open: boolean;
  onClose: () => void;
  content: ContentRead;
  onWatch: (jobId: string) => void;
}) {
  const [scope, setScope] = useState<RegenerationScope>("FULL");
  const [instruction, setInstruction] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const availableScopes = (Object.keys(SCOPE_LABELS) as RegenerationScope[]).filter(
    (s) => s !== "HOOK" || content.format === "REEL"
  );

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const { job_id } = await contentsApi.regenerate(content.id, { scope, instruction: instruction || null });
      onClose();
      onWatch(job_id);
      setInstruction("");
      setScope("FULL");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erro ao regenerar.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Regenerar conteudo"
      description="A IA reescreve apenas o escopo escolhido, preservando o resto."
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} loading={submitting} icon={<RefreshCw className="h-4 w-4" />}>
            Regenerar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <Label>O que reescrever</Label>
          <Select value={scope} onChange={(event) => setScope(event.target.value as RegenerationScope)}>
            {availableScopes.map((value) => (
              <option key={value} value={value}>
                {SCOPE_LABELS[value]}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label>Instrucao (opcional)</Label>
          <Textarea
            rows={3}
            placeholder='Ex.: "deixe o roteiro mais curto e direto"'
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
          />
        </div>
      </div>
    </Dialog>
  );
}

function ChangeFormatDialog({
  open,
  onClose,
  content,
  onWatch,
  onComplete,
}: {
  open: boolean;
  onClose: () => void;
  content: ContentRead;
  onWatch: (jobId: string) => void;
  onComplete: (content: ContentRead) => void;
}) {
  const [format, setFormat] = useState<ContentFormat>(content.format);
  const [regenerate, setRegenerate] = useState(true);
  const [instruction, setInstruction] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    if (format === content.format) {
      toast.info("Escolha um formato diferente do atual.");
      return;
    }
    setSubmitting(true);
    try {
      const response = await contentsApi.changeFormat(content.id, { format, regenerate, instruction: instruction || null });
      onComplete(response.content);
      onClose();
      if (response.job_id) onWatch(response.job_id);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erro ao trocar formato.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Trocar formato"
      description="O payload atual e reiniciado. Com a reescrita ativa, a IA recria o conteudo no novo formato."
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} loading={submitting}>
            Confirmar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <Label>Novo formato</Label>
          <Select value={format} onChange={(event) => setFormat(event.target.value as ContentFormat)}>
            <option value="REEL">Reel</option>
            <option value="IMAGE_POST">Post</option>
            <option value="CAROUSEL">Carrossel</option>
            <option value="STORY">Story</option>
          </Select>
        </div>
        <label className="flex items-center gap-2 text-sm text-foreground/70">
          <input type="checkbox" className="h-4 w-4 rounded" checked={regenerate} onChange={(event) => setRegenerate(event.target.checked)} />
          Reescrever com IA no novo formato
        </label>
        {regenerate && (
          <div>
            <Label>Instrucao (opcional)</Label>
            <Textarea rows={2} value={instruction} onChange={(event) => setInstruction(event.target.value)} />
          </div>
        )}
      </div>
    </Dialog>
  );
}

function VersionsDialog({
  open,
  onClose,
  contentId,
  onRestored,
}: {
  open: boolean;
  onClose: () => void;
  contentId: string;
  onRestored: (content: ContentRead) => void;
}) {
  const { data: versions, isLoading } = useQuery({
    queryKey: queryKeys.contentVersions(contentId),
    queryFn: () => contentsApi.versions(contentId),
    enabled: open,
  });

  const restoreMutation = useMutation({
    mutationFn: (version: number) => contentsApi.restoreVersion(contentId, version),
    onSuccess: (content) => {
      toast.success(`Versao ${content.current_version} restaurada.`);
      onRestored(content);
    },
    onError: (error: unknown) => toast.error(error instanceof ApiError ? error.message : "Erro ao restaurar versao."),
  });

  return (
    <Dialog open={open} onClose={onClose} title="Historico de versoes" className="max-w-xl">
      {isLoading ? (
        <PageSpinner />
      ) : !versions || versions.length === 0 ? (
        <p className="py-8 text-center text-sm text-foreground/50">Nenhuma versao registrada ainda.</p>
      ) : (
        <div className="max-h-96 space-y-2 overflow-y-auto scrollbar-thin">
          {versions
            .slice()
            .sort((a, b) => b.version - a.version)
            .map((version) => (
              <div key={version.id} className="flex items-center justify-between gap-3 rounded-xl border border-border-subtle p-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground">
                    Versao {version.version} - {AUTHOR_LABEL[version.author]}
                  </p>
                  <p className="text-xs text-foreground/50">
                    {formatDateTime(version.created_at)}
                    {version.regeneration_scope && ` - escopo: ${SCOPE_LABELS[version.regeneration_scope]}`}
                  </p>
                  {version.change_reason && <p className="mt-1 text-xs text-foreground/60">{version.change_reason}</p>}
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => restoreMutation.mutate(version.version)}
                  loading={restoreMutation.isPending && restoreMutation.variables === version.version}
                >
                  Restaurar
                </Button>
              </div>
            ))}
        </div>
      )}
    </Dialog>
  );
}

const AUTHOR_LABEL: Record<string, string> = { USER: "Manual", AI: "IA", SYSTEM: "Sistema" };

function AssetPickerDialog({
  open,
  onClose,
  onPick,
  excludeIds,
}: {
  open: boolean;
  onClose: () => void;
  onPick: (assetId: string) => Promise<void>;
  excludeIds: string[];
}) {
  const { data: assets, isLoading } = useQuery({
    queryKey: queryKeys.assets(),
    queryFn: () => assetsApi.list(),
    enabled: open,
  });
  const [pickingId, setPickingId] = useState<string | null>(null);

  const available = assets?.filter((asset) => !excludeIds.includes(asset.id)) ?? [];

  async function handlePick(assetId: string) {
    setPickingId(assetId);
    try {
      await onPick(assetId);
    } finally {
      setPickingId(null);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="Vincular imagem" className="max-w-xl">
      {isLoading ? (
        <PageSpinner />
      ) : available.length === 0 ? (
        <p className="py-8 text-center text-sm text-foreground/50">
          Nenhuma imagem disponivel. Envie imagens na Biblioteca de Imagens.
        </p>
      ) : (
        <div className="grid max-h-96 grid-cols-3 gap-2 overflow-y-auto scrollbar-thin sm:grid-cols-4">
          {available.map((asset) => (
            <button
              key={asset.id}
              onClick={() => handlePick(asset.id)}
              disabled={pickingId !== null}
              className="group relative aspect-square overflow-hidden rounded-lg border border-border-subtle"
            >
              {asset.url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={asset.url} alt={asset.alt_text ?? ""} className="h-full w-full object-cover" />
              )}
              <div className="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition-opacity group-hover:bg-black/40 group-hover:opacity-100">
                {pickingId === asset.id ? (
                  <RefreshCw className="h-5 w-5 animate-spin text-white" />
                ) : (
                  <Check className="h-5 w-5 text-white" />
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </Dialog>
  );
}
