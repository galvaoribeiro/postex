"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Boxes, Pencil, Plus, Trash2 } from "lucide-react";
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
import { FieldError, Input, Label, Textarea } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { TagInput } from "@/components/ui/tag-input";
import { productsApi } from "@/lib/api/catalog";
import { ApiError } from "@/lib/api/client";
import type { ProductPayload, ProductRead } from "@/lib/api/types";
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

export default function ProductsPage() {
  const queryClient = useQueryClient();
  const { data: products, isLoading } = useQuery({
    queryKey: queryKeys.products,
    queryFn: () => productsApi.list(),
  });

  const [editing, setEditing] = useState<ProductRead | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [deleting, setDeleting] = useState<ProductRead | null>(null);

  const createMutation = useMutation({
    mutationFn: productsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.products });
      toast.success("Produto criado.");
      setFormOpen(false);
    },
    onError: (error: unknown) => toast.error(error instanceof ApiError ? error.message : "Erro ao criar produto."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<ProductPayload> }) =>
      productsApi.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.products });
      toast.success("Produto atualizado.");
      setFormOpen(false);
    },
    onError: (error: unknown) => toast.error(error instanceof ApiError ? error.message : "Erro ao atualizar."),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => productsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.products });
      toast.success("Produto removido.");
      setDeleting(null);
    },
  });

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(product: ProductRead) {
    setEditing(product);
    setFormOpen(true);
  }

  return (
    <div>
      <PageHeader
        title="Produtos"
        description="O catalogo que o Motor de Conteudo usa para gerar ideias e conteudos especificos."
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={openCreate}>
            Novo produto
          </Button>
        }
      />

      {isLoading ? (
        <PageSpinner />
      ) : !products || products.length === 0 ? (
        <EmptyState
          icon={Boxes}
          title="Nenhum produto cadastrado"
          description="Cadastre seus produtos para que a IA crie conteudos especificos sobre eles."
          action={<Button onClick={openCreate}>Cadastrar produto</Button>}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((product) => (
            <Card key={product.id}>
              <CardContent className="space-y-3 p-5">
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
          ))}
        </div>
      )}

      <ProductFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        product={editing}
        loading={createMutation.isPending || updateMutation.isPending}
        onSubmit={(values) => {
          const payload: ProductPayload = {
            ...values,
            description: values.description || null,
            category: values.category || null,
            price: values.price === "" || values.price === undefined ? null : Number(values.price),
          };
          if (editing) {
            updateMutation.mutate({ id: editing.id, payload });
          } else {
            createMutation.mutate(payload);
          }
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
  onSubmit,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  product: ProductRead | null;
  onSubmit: (values: FormValues) => void;
  loading: boolean;
}) {
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

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={product ? "Editar produto" : "Novo produto"}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit(onSubmit)} loading={loading}>
            Salvar
          </Button>
        </>
      }
    >
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
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
