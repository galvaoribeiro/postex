"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Notebook, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { ContentStatusBadge } from "@/components/domain/status-badge";
import { FormatBadge } from "@/components/domain/format-badge";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { FieldError, Input, Label } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { Select } from "@/components/ui/select";
import { contentsApi } from "@/lib/api/contents";
import { ApiError } from "@/lib/api/client";
import type { ContentFormat, ContentStatus } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";

const STATUS_OPTIONS: { value: ContentStatus | ""; label: string }[] = [
  { value: "", label: "Todos os status" },
  { value: "DRAFT", label: "Rascunho" },
  { value: "REVIEW", label: "Em revisao" },
  { value: "APPROVED", label: "Aprovado" },
  { value: "SCHEDULED", label: "Agendado" },
  { value: "PUBLISHED", label: "Publicado" },
  { value: "REJECTED", label: "Rejeitado" },
  { value: "ARCHIVED", label: "Arquivado" },
];

const FORMAT_OPTIONS: { value: ContentFormat | ""; label: string }[] = [
  { value: "", label: "Todos os formatos" },
  { value: "REEL", label: "Reel" },
  { value: "IMAGE_POST", label: "Post" },
  { value: "CAROUSEL", label: "Carrossel" },
  { value: "STORY", label: "Story" },
];

export default function ContentsPage() {
  const [status, setStatus] = useState<ContentStatus | "">("");
  const [format, setFormat] = useState<ContentFormat | "">("");
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.contents({ status, format, search }),
    queryFn: () =>
      contentsApi.list({
        status: status ? [status] : undefined,
        format: format ? [format] : undefined,
        search: search || undefined,
        limit: 100,
      }),
  });

  return (
    <div>
      <PageHeader
        title="Conteudos"
        description="Todo o conteudo criado, do rascunho ao publicado."
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => setCreateOpen(true)}>
            Criar do zero
          </Button>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground/40" />
          <Input
            placeholder="Buscar por titulo..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="pl-9"
          />
        </div>
        <Select
          value={status}
          onChange={(event) => setStatus(event.target.value as ContentStatus)}
          className="w-auto"
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.label} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
        <Select
          value={format}
          onChange={(event) => setFormat(event.target.value as ContentFormat)}
          className="w-auto"
        >
          {FORMAT_OPTIONS.map((option) => (
            <option key={option.label} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </div>

      {isLoading ? (
        <PageSpinner />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={Notebook}
          title="Nenhum conteudo encontrado"
          description="Gere ideias e transforme-as em conteudo, ou crie um conteudo do zero."
          action={<Button onClick={() => setCreateOpen(true)}>Criar conteudo</Button>}
        />
      ) : (
        <Card>
          <CardContent className="divide-y divide-border-subtle p-0">
            {data.items.map((content) => (
              <Link
                key={content.id}
                href={`/contents/${content.id}`}
                className="flex items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-surface-muted/60"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-foreground">{content.title}</p>
                  <div className="mt-1 flex items-center gap-2 text-xs text-foreground/50">
                    {content.category && <span>{content.category}</span>}
                    <span>v{content.current_version}</span>
                    <span>Atualizado em {formatDate(content.updated_at)}</span>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <FormatBadge format={content.format} />
                  <ContentStatusBadge status={content.status} />
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>
      )}

      <CreateContentDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}

const createSchema = z.object({
  title: z.string().min(2, "Informe um titulo.").max(240),
  format: z.enum(["REEL", "IMAGE_POST", "CAROUSEL", "STORY"]),
  category: z.string().max(64).optional().or(z.literal("")),
  concept: z.string().max(2000).optional().or(z.literal("")),
});

type CreateFormValues = z.infer<typeof createSchema>;

function CreateContentDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateFormValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { title: "", format: "IMAGE_POST", category: "", concept: "" },
  });

  const createMutation = useMutation({
    mutationFn: contentsApi.createManual,
    onSuccess: (content) => {
      queryClient.invalidateQueries({ queryKey: ["contents"] });
      toast.success("Conteudo criado.");
      reset();
      onClose();
      router.push(`/contents/${content.id}`);
    },
    onError: (error: unknown) => toast.error(error instanceof ApiError ? error.message : "Erro ao criar conteudo."),
  });

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Criar conteudo do zero"
      description="Sem passar pela IA. Voce podera pedir regeneracao depois."
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit((values) => createMutation.mutate(values))} loading={createMutation.isPending}>
            Criar
          </Button>
        </>
      }
    >
      <form className="space-y-4">
        <div>
          <Label htmlFor="c_title">Titulo</Label>
          <Input id="c_title" {...register("title")} />
          <FieldError>{errors.title?.message}</FieldError>
        </div>
        <div>
          <Label htmlFor="c_format">Formato</Label>
          <Select id="c_format" {...register("format")}>
            <option value="REEL">Reel</option>
            <option value="IMAGE_POST">Post</option>
            <option value="CAROUSEL">Carrossel</option>
            <option value="STORY">Story</option>
          </Select>
        </div>
        <div>
          <Label htmlFor="c_category">Categoria (opcional)</Label>
          <Input id="c_category" {...register("category")} />
        </div>
      </form>
    </Dialog>
  );
}

