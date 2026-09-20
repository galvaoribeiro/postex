"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Boxes, ImagePlus, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { FieldError, FieldHint, Input, Label, Textarea } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { TagInput } from "@/components/ui/tag-input";
import { assetsApi, uploadLinkedImage } from "@/lib/api/assets";
import { productsApi } from "@/lib/api/catalog";
import { ApiError } from "@/lib/api/client";
import type { AssetRead, ProductPayload, ProductRead } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";
import { formatCurrency } from "@/lib/utils";

const schema = z.object({
  name: z.string().min(2, "Informe o nome.").max(160),
  description: z.string().max(2000).optional().or(z.literal("")),
  category: z.string().max(120).optional().or(z.literal("")),
  price: z
    .string()
    .optional()
    .refine((value) => !value || (!Number.isNaN(Number(value)) && Number(value) >= 0), "Preco invalido."),
  currency: z.string().length(3),
  highlights: z.array(z.string()),
  is_active: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

function photoUrlFor(assets: AssetRead[] | undefined, productId: string): string | null {
  return (
    assets?.find(
      (asset) =>
        asset.product_id === productId &&
        asset.status === "READY" &&
        asset.mime_type.startsWith("image/") &&
        asset.url
    )?.url ?? null
  );
}

export default function ProductsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: products, isLoading } = useQuery({
    queryKey: queryKeys.products,
    queryFn: () => productsApi.list(),
  });
  const { data: assets } = useQuery({
    queryKey: queryKeys.assets({ kind: "PRODUCT_PHOTO" }),
    queryFn: () => assetsApi.list({ kind: "PRODUCT_PHOTO", status: "READY" }),
  });

  const [editing, setEditing] = useState<ProductRead | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [deleting, setDeleting] = useState<ProductRead | null>(null);

  const updateMutation = useMutation({
    mutationFn: async ({
      id,
      payload,
      photo,
    }: {
      id: string;
      payload: Partial<ProductPayload>;
      photo: File | null;
    }) => {
      const updated = await productsApi.update(id, payload);
      if (photo) {
        await uploadLinkedImage(photo, { kind: "PRODUCT_PHOTO", productId: id });
      }
      return updated;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.products });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      toast.success("Produto atualizado.");
      setFormOpen(false);
    },
    onError: (error: unknown) => toast.error(error instanceof ApiError ? error.message : "Erro ao atualizar."),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => productsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.products });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      toast.success("Produto removido.");
      setDeleting(null);
    },
  });

  function openEdit(product: ProductRead) {
    setEditing(product);
    setFormOpen(true);
  }

  return (
    <div>
      <PageHeader
        title="Produtos"
        description="Edite, troque a foto ou exclua produtos ja cadastrados. O cadastro novo acontece em Criar."
      />

      {isLoading ? (
        <PageSpinner />
      ) : !products || products.length === 0 ? (
        <EmptyState
          icon={Boxes}
          title="Nenhum produto cadastrado"
          description="Cadastre o produto em Criar, com a foto. Depois voce edita por aqui."
          action={<Button onClick={() => router.push("/criar")}>Ir para Criar</Button>}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((product) => {
            const photoUrl = photoUrlFor(assets, product.id);
            return (
              <Card key={product.id}>
                <CardContent className="space-y-3 p-5">
                  {photoUrl && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={photoUrl}
                      alt={product.name}
                      className="h-36 w-full rounded-xl object-cover"
                    />
                  )}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-semibold text-foreground">{product.name}</p>
                      {product.category && <p className="text-xs text-foreground/45">{product.category}</p>}
                    </div>
                    <div className="flex gap-1">
                      <Button size="icon" variant="ghost" onClick={() => openEdit(product)} aria-label="Editar">
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => setDeleting(product)}
                        aria-label="Excluir"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  {product.description && (
                    <p className="line-clamp-2 text-sm text-foreground/60">{product.description}</p>
                  )}
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-brand-700">
                      {formatCurrency(product.price, product.currency)}
                    </span>
                    {!product.is_active && (
                      <span className="rounded-full bg-surface-muted px-2 py-0.5 text-xs text-foreground/50">
                        Inativo
                      </span>
                    )}
                  </div>
                  {product.highlights.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {product.highlights.map((highlight) => (
                        <span
                          key={highlight}
                          className="rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700"
                        >
                          {highlight}
                        </span>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <ProductFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        product={editing}
        photoUrl={editing ? photoUrlFor(assets, editing.id) : null}
        loading={updateMutation.isPending}
        onSubmit={(values, photo) => {
          if (!editing) return;
          const payload: ProductPayload = {
            ...values,
            description: values.description || null,
            category: values.category || null,
            price: values.price === "" || values.price === undefined ? null : Number(values.price),
          };
          updateMutation.mutate({ id: editing.id, payload, photo });
        }}
      />

      <ConfirmDialog
        open={Boolean(deleting)}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && removeMutation.mutate(deleting.id)}
        title="Remover produto"
        description={`Tem certeza que deseja remover "${deleting?.name}"? Essa acao nao pode ser desfeita.`}
        confirmLabel="Remover"
        danger
        loading={removeMutation.isPending}
      />
    </div>
  );
}

function ProductFormDialog({
  open,
  onClose,
  product,
  photoUrl,
  onSubmit,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  product: ProductRead | null;
  photoUrl: string | null;
  onSubmit: (values: FormValues, photo: File | null) => void;
  loading: boolean;
}) {
  const [photo, setPhoto] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", currency: "BRL", highlights: [], is_active: true },
  });

  useEffect(() => {
    if (open) {
      setPhoto(null);
      setPreview(null);
      reset(
        product
          ? {
              name: product.name,
              description: product.description ?? "",
              category: product.category ?? "",
              price: product.price !== null ? String(product.price) : "",
              currency: product.currency,
              highlights: product.highlights,
              is_active: product.is_active,
            }
          : { name: "", description: "", category: "", price: "", currency: "BRL", highlights: [], is_active: true }
      );
    }
  }, [open, product, reset]);

  useEffect(() => {
    if (!photo) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(photo);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Editar produto"
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit((values) => onSubmit(values, photo))} loading={loading}>
            Salvar
          </Button>
        </>
      }
    >
      <form className="space-y-4" onSubmit={handleSubmit((values) => onSubmit(values, photo))}>
        <div>
          <Label htmlFor="p_photo">Foto do produto</Label>
          <label
            htmlFor="p_photo"
            className="mt-1 flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-border-subtle px-3 py-3 text-sm hover:border-brand-300"
          >
            {preview || photoUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={preview || photoUrl || ""}
                alt=""
                className="h-14 w-14 rounded-lg object-cover"
              />
            ) : (
              <span className="flex h-14 w-14 items-center justify-center rounded-lg bg-surface-muted text-foreground/45">
                <ImagePlus className="h-5 w-5" />
              </span>
            )}
            <span className="text-foreground/70">
              {photo ? photo.name : "Trocar foto (usada na capa em Criar)"}
            </span>
          </label>
          <input
            id="p_photo"
            type="file"
            accept="image/*"
            className="sr-only"
            onChange={(event) => setPhoto(event.target.files?.[0] ?? null)}
          />
          <FieldHint>Altere nome, preco e foto dos produtos ja cadastrados. Novos produtos nascem em Criar.</FieldHint>
        </div>
        <div>
          <Label htmlFor="p_name">Nome</Label>
          <Input id="p_name" {...register("name")} />
          <FieldError>{errors.name?.message}</FieldError>
        </div>
        <div>
          <Label htmlFor="p_description">Descricao</Label>
          <Textarea id="p_description" rows={3} {...register("description")} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="p_category">Categoria</Label>
            <Input id="p_category" {...register("category")} />
          </div>
          <div>
            <Label htmlFor="p_price">Preco</Label>
            <Input id="p_price" type="number" step="0.01" min={0} {...register("price")} />
          </div>
        </div>
        <div>
          <Label>Destaques</Label>
          <Controller
            control={control}
            name="highlights"
            render={({ field }) => (
              <TagInput value={field.value} onChange={field.onChange} placeholder="Ex.: Feito na hora" />
            )}
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-foreground/70">
          <input type="checkbox" className="h-4 w-4 rounded" {...register("is_active")} />
          Produto ativo
        </label>
      </form>
    </Dialog>
  );
}
