"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Lightbulb, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { IdeaCard } from "@/components/domain/idea-card";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { FieldHint, Input, Label, Textarea } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { Select } from "@/components/ui/select";
import { aiApi } from "@/lib/api/ai";
import { contentsApi } from "@/lib/api/contents";
import { ApiError } from "@/lib/api/client";
import { ideasApi } from "@/lib/api/ideas";
import { useJobWatcher } from "@/lib/hooks/use-job-watcher";
import type { ContentFormat, ContentIdeaRead, IdeaStatus } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";
import { cn } from "@/lib/utils";

export default function IdeasPage() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { watch } = useJobWatcher();

  const [statusFilter, setStatusFilter] = useState<IdeaStatus | "">("AVAILABLE");
  const [generateOpen, setGenerateOpen] = useState(false);
  const [producingIdeaId, setProducingIdeaId] = useState<string | null>(null);

  const { data: ideas, isLoading } = useQuery({
    queryKey: queryKeys.ideas({ status: statusFilter }),
    queryFn: () => ideasApi.list(statusFilter ? { status: statusFilter, limit: 100 } : { limit: 100 }),
  });

  const discardMutation = useMutation({
    mutationFn: (idea: ContentIdeaRead) => ideasApi.setStatus(idea.id, "DISCARDED"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ideas"] });
      toast.success("Ideia descartada.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (idea: ContentIdeaRead) => ideasApi.remove(idea.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ideas"] });
      toast.success("Ideia excluida.");
    },
  });

  const produceMutation = useMutation({
    mutationFn: (idea: ContentIdeaRead) => contentsApi.createFromIdea({ idea_id: idea.id }),
    onSuccess: async ({ job_id }) => {
      const job = await watch(job_id, "CONTENT_PRODUCTION", {
        loadingMessage: "Produzindo conteudo a partir da ideia...",
        successMessage: "Conteudo criado! Abrindo editor...",
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ideas"] }),
      });
      const contentId = job?.result?.content_id as string | undefined;
      if (contentId) router.push(`/contents/${contentId}`);
      setProducingIdeaId(null);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : "Nao foi possivel produzir o conteudo.");
      setProducingIdeaId(null);
    },
  });

  function handleUse(idea: ContentIdeaRead) {
    setProducingIdeaId(idea.id);
    produceMutation.mutate(idea);
  }

  return (
    <div>
      <PageHeader
        title="Ideias"
        description="O Motor de Conteudo sugere ideias especificas para o seu negocio. Escolha uma e transforme em conteudo."
        actions={
          <Button icon={<Sparkles className="h-4 w-4" />} onClick={() => setGenerateOpen(true)}>
            Gerar ideias
          </Button>
        }
      />

      <div className="mb-5 flex gap-2">
        {(
          [
            { value: "AVAILABLE", label: "Disponiveis" },
            { value: "USED", label: "Usadas" },
            { value: "DISCARDED", label: "Descartadas" },
            { value: "", label: "Todas" },
          ] as const
        ).map((option) => (
          <button
            key={option.label}
            onClick={() => setStatusFilter(option.value)}
            className={cn(
              "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
              statusFilter === option.value
                ? "border-brand-500 bg-brand-50 text-brand-700"
                : "border-border-subtle text-foreground/55 hover:border-brand-200"
            )}
          >
            {option.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <PageSpinner />
      ) : !ideas || ideas.length === 0 ? (
        <EmptyState
          icon={Lightbulb}
          title="Nenhuma ideia por aqui"
          description="Gere ideias com o Motor de Conteudo com base no contexto do seu negocio."
          action={<Button onClick={() => setGenerateOpen(true)}>Gerar ideias</Button>}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {ideas.map((idea) => (
            <IdeaCard
              key={idea.id}
              idea={idea}
              busy={producingIdeaId === idea.id}
              onUse={handleUse}
              onDiscard={(target) => discardMutation.mutate(target)}
              onDelete={(target) => deleteMutation.mutate(target)}
            />
          ))}
        </div>
      )}

      <GenerateIdeasDialog open={generateOpen} onClose={() => setGenerateOpen(false)} />
    </div>
  );
}

function GenerateIdeasDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const { watch } = useJobWatcher();
  const [count, setCount] = useState(5);
  const [categories, setCategories] = useState<string[]>([]);
  const [formatHint, setFormatHint] = useState<ContentFormat | "">("");
  const [instruction, setInstruction] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const { data: taxonomy } = useQuery({ queryKey: queryKeys.taxonomy, queryFn: aiApi.taxonomy });

  function toggleCategory(key: string) {
    setCategories((prev) => (prev.includes(key) ? prev.filter((c) => c !== key) : [...prev, key]));
  }

  async function handleGenerate() {
    setSubmitting(true);
    try {
      const { job_id } = await ideasApi.generate({
        count,
        categories,
        format_hint: formatHint || null,
        instruction: instruction || null,
      });
      onClose();
      await watch(job_id, "IDEATION", {
        loadingMessage: "Gerando ideias com o Motor de Conteudo...",
        successMessage: (job) => `${(job.result?.count as number) ?? count} ideias geradas!`,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ideas"] }),
      });
      setCategories([]);
      setInstruction("");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Nao foi possivel gerar ideias.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Gerar novas ideias"
      description="O motor considera o contexto do seu negocio para sugerir ideias especificas."
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button onClick={handleGenerate} loading={submitting} icon={<Sparkles className="h-4 w-4" />}>
            Gerar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <Label htmlFor="count">Quantidade de ideias</Label>
          <Input
            id="count"
            type="number"
            min={1}
            max={12}
            value={count}
            onChange={(event) => setCount(Number(event.target.value))}
          />
        </div>

        <div>
          <Label htmlFor="format_hint">Formato preferido (opcional)</Label>
          <Select
            id="format_hint"
            value={formatHint}
            onChange={(event) => setFormatHint(event.target.value as ContentFormat)}
          >
            <option value="">Deixar o motor decidir</option>
            <option value="REEL">Reel</option>
            <option value="IMAGE_POST">Post</option>
            <option value="CAROUSEL">Carrossel</option>
            <option value="STORY">Story</option>
          </Select>
        </div>

        {taxonomy && (
          <div>
            <Label>Pilares editoriais (opcional)</Label>
            <FieldHint>Vazio deixa o motor distribuir entre os pilares.</FieldHint>
            <div className="mt-2 flex max-h-40 flex-wrap gap-1.5 overflow-y-auto scrollbar-thin">
              {taxonomy.categories.map((category) => (
                <button
                  key={category.key}
                  type="button"
                  onClick={() => toggleCategory(category.key)}
                  className={cn(
                    "rounded-full border px-2.5 py-1 text-xs font-medium",
                    categories.includes(category.key)
                      ? "border-brand-500 bg-brand-50 text-brand-700"
                      : "border-border-subtle text-foreground/55 hover:border-brand-200"
                  )}
                  title={category.description}
                >
                  {category.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <div>
          <Label htmlFor="instruction">Instrucao extra (opcional)</Label>
          <Textarea
            id="instruction"
            rows={2}
            placeholder='Ex.: "Foque em promover o novo cardapio de verao"'
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
          />
        </div>
      </div>
    </Dialog>
  );
}
