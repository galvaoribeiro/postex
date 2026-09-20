"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Image as ImageIcon, Sparkles, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { FieldHint, Input, Label, Textarea } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { Select } from "@/components/ui/select";
import { TagInput } from "@/components/ui/tag-input";
import { assetsApi, readImageDimensions, uploadFileToSignedUrl } from "@/lib/api/assets";
import { productsApi, servicesApi } from "@/lib/api/catalog";
import { ApiError } from "@/lib/api/client";
import { useJobWatcher } from "@/lib/hooks/use-job-watcher";
import type { AssetKind, AssetRead } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";
import { cn } from "@/lib/utils";

const KIND_LABELS: Record<AssetKind, string> = {
  PRODUCT_PHOTO: "Foto de produto",
  PLACE_PHOTO: "Foto do estabelecimento",
  TEAM_PHOTO: "Foto da equipe",
  LOGO: "Logo",
  REFERENCE: "Referencia",
  AI_GENERATED: "Gerada por IA",
  MODEL_PHOTO: "Modelo",
  VIDEO_GENERATED: "Video gerado",
  THUMBNAIL: "Thumbnail",
  OTHER: "Outro",
};

export default function AssetsPage() {
  const queryClient = useQueryClient();
  const [kindFilter, setKindFilter] = useState<AssetKind | "">("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [deleting, setDeleting] = useState<AssetRead | null>(null);
  const { watch } = useJobWatcher();

  const { data: assets, isLoading } = useQuery({
    queryKey: queryKeys.assets({ kind: kindFilter }),
    queryFn: () => assetsApi.list(kindFilter ? { kind: kindFilter } : undefined),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => assetsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      toast.success("Imagem removida.");
      setDeleting(null);
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: (id: string) => assetsApi.analyze(id),
    onSuccess: async ({ job_id }) => {
      await watch(job_id, "ASSET_ANALYSIS", {
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assets"] }),
      });
    },
    onError: (error: unknown) => toast.error(error instanceof ApiError ? error.message : "Erro ao analisar."),
  });

  return (
    <div>
      <PageHeader
        title="Biblioteca de Imagens"
        description="Fotos do espaco, equipe, modelos e extras. As modelos geradas na criacao ficam aqui, inclusive as que voce nao aprovou. A foto do produto e anexada em Criar."
        actions={
          <Button icon={<Upload className="h-4 w-4" />} onClick={() => setUploadOpen(true)}>
            Enviar imagem
          </Button>
        }
      />

      <div className="mb-5 flex flex-wrap gap-2">
        <FilterChip active={kindFilter === ""} onClick={() => setKindFilter("")}>
          Todas
        </FilterChip>
        {Object.entries(KIND_LABELS).map(([kind, label]) => (
          <FilterChip key={kind} active={kindFilter === kind} onClick={() => setKindFilter(kind as AssetKind)}>
            {label}
          </FilterChip>
        ))}
      </div>

      {isLoading ? (
        <PageSpinner />
      ) : !assets || assets.length === 0 ? (
        <EmptyState
          icon={ImageIcon}
          title="Nenhuma imagem ainda"
          description="Envie fotos dos seus produtos, do espaco ou da equipe para enriquecer o contexto da IA."
          action={<Button onClick={() => setUploadOpen(true)}>Enviar primeira imagem</Button>}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {assets.map((asset) => (
            <Card key={asset.id} className="overflow-hidden">
              <div className="relative aspect-square bg-surface-muted">
                {asset.url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={asset.url} alt={asset.alt_text ?? asset.original_filename} className="h-full w-full object-cover" />
                ) : (
                  <div className="flex h-full items-center justify-center text-foreground/30">
                    <ImageIcon className="h-8 w-8" />
                  </div>
                )}
                <button
                  onClick={() => setDeleting(asset)}
                  className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-full bg-black/50 text-white hover:bg-danger-fg"
                  aria-label="Excluir imagem"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <CardContent className="space-y-2 p-3">
                <p className="truncate text-sm font-medium text-foreground">
                  {asset.title || asset.original_filename}
                </p>
                <Badge tone="neutral">{KIND_LABELS[asset.kind]}</Badge>
                {asset.ai_analysis?.summary ? (
                  <p className="line-clamp-2 text-xs text-foreground/55">
                    {String(asset.ai_analysis.summary)}
                  </p>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full"
                    icon={<Sparkles className="h-3.5 w-3.5" />}
                    onClick={() => analyzeMutation.mutate(asset.id)}
                    loading={analyzeMutation.isPending && analyzeMutation.variables === asset.id}
                  >
                    Analisar com IA
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <UploadDialog open={uploadOpen} onClose={() => setUploadOpen(false)} />

      <ConfirmDialog
        open={Boolean(deleting)}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && removeMutation.mutate(deleting.id)}
        title="Remover imagem"
        description="Essa imagem sera removida da biblioteca e de qualquer conteudo vinculado."
        confirmLabel="Remover"
        danger
        loading={removeMutation.isPending}
      />
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
        active
          ? "border-brand-500 bg-brand-50 text-brand-700"
          : "border-border-subtle text-foreground/55 hover:border-brand-200"
      )}
    >
      {children}
    </button>
  );
}

function UploadDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [kind, setKind] = useState<AssetKind>("PRODUCT_PHOTO");
  const [title, setTitle] = useState("");
  const [altText, setAltText] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [productId, setProductId] = useState("");
  const [serviceId, setServiceId] = useState("");
  const [analyze, setAnalyze] = useState(true);
  const [uploading, setUploading] = useState(false);
  const { watch } = useJobWatcher();

  const { data: products } = useQuery({ queryKey: queryKeys.products, queryFn: () => productsApi.list() });
  const { data: services } = useQuery({ queryKey: queryKeys.services, queryFn: () => servicesApi.list() });

  function reset() {
    setFile(null);
    setKind("PRODUCT_PHOTO");
    setTitle("");
    setAltText("");
    setTags([]);
    setProductId("");
    setServiceId("");
    setAnalyze(true);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleClose() {
    reset();
    onClose();
  }

  async function handleUpload() {
    if (!file) {
      toast.error("Selecione um arquivo.");
      return;
    }
    setUploading(true);
    try {
      const ticket = await assetsApi.createUploadUrl({
        filename: file.name,
        mime_type: file.type || "application/octet-stream",
        size_bytes: file.size,
        kind,
        title: title || undefined,
        alt_text: altText || undefined,
        tags,
        product_id: productId || null,
        service_id: serviceId || null,
      });

      await uploadFileToSignedUrl(ticket, file);
      const dimensions = await readImageDimensions(file);

      await assetsApi.confirm(ticket.asset_id, {
        size_bytes: file.size,
        width: dimensions?.width,
        height: dimensions?.height,
        analyze: false,
      });

      queryClient.invalidateQueries({ queryKey: ["assets"] });
      toast.success("Imagem enviada.");
      handleClose();

      if (analyze) {
        const { job_id } = await assetsApi.analyze(ticket.asset_id);
        watch(job_id, "ASSET_ANALYSIS", {
          onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assets"] }),
        });
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao enviar a imagem.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      title="Enviar imagem"
      description="A imagem vai direto para o storage e passa a servir de contexto para a IA."
      footer={
        <>
          <Button variant="outline" onClick={handleClose} disabled={uploading}>
            Cancelar
          </Button>
          <Button onClick={handleUpload} loading={uploading}>
            Enviar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <Label htmlFor="file">Arquivo</Label>
          <input
            id="file"
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="block w-full text-sm text-foreground/70"
          />
          <FieldHint>JPG, PNG ou WebP, ate 15MB.</FieldHint>
        </div>

        <div>
          <Label htmlFor="kind">Tipo de imagem</Label>
          <Select id="kind" value={kind} onChange={(event) => setKind(event.target.value as AssetKind)}>
            {Object.entries(KIND_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="link_product">Vincular a produto</Label>
            <Select id="link_product" value={productId} onChange={(event) => setProductId(event.target.value)}>
              <option value="">Nenhum</option>
              {products?.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="link_service">Vincular a servico</Label>
            <Select id="link_service" value={serviceId} onChange={(event) => setServiceId(event.target.value)}>
              <option value="">Nenhum</option>
              {services?.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.name}
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div>
          <Label htmlFor="title">Titulo (opcional)</Label>
          <Input id="title" value={title} onChange={(event) => setTitle(event.target.value)} />
        </div>
        <div>
          <Label htmlFor="alt">Descricao / alt text</Label>
          <Textarea id="alt" rows={2} value={altText} onChange={(event) => setAltText(event.target.value)} />
        </div>
        <div>
          <Label>Tags</Label>
          <TagInput value={tags} onChange={setTags} />
        </div>
        <label className="flex items-center gap-2 text-sm text-foreground/70">
          <input
            type="checkbox"
            className="h-4 w-4 rounded"
            checked={analyze}
            onChange={(event) => setAnalyze(event.target.checked)}
          />
          Analisar com IA apos o envio
        </label>
      </div>
    </Dialog>
  );
}
