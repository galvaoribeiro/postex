"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock, Pencil, Plus, Trash2, Wrench } from "lucide-react";
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
import { servicesApi } from "@/lib/api/catalog";
import { ApiError } from "@/lib/api/client";
import type { ServicePayload, ServiceRead } from "@/lib/api/types";
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
  duration_minutes: z
    .string()
    .optional()
    .refine((value) => !value || (!Number.isNaN(Number(value)) && Number(value) >= 1), "Duracao invalida."),
  deliverables: z.array(z.string()),
  is_active: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

export default function ServicesPage() {
  const queryClient = useQueryClient();
  const { data: services, isLoading } = useQuery({
    queryKey: queryKeys.services,
    queryFn: () => servicesApi.list(),
  });

  const [editing, setEditing] = useState<ServiceRead | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [deleting, setDeleting] = useState<ServiceRead | null>(null);

  const createMutation = useMutation({
    mutationFn: servicesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.services });
      toast.success("Servico criado.");
      setFormOpen(false);
    },
    onError: (error: unknown) => toast.error(error instanceof ApiError ? error.message : "Erro ao criar servico."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<ServicePayload> }) =>
      servicesApi.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.services });
      toast.success("Servico atualizado.");
      setFormOpen(false);
    },
    onError: (error: unknown) => toast.error(error instanceof ApiError ? error.message : "Erro ao atualizar."),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => servicesApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.services });
      toast.success("Servico removido.");
      setDeleting(null);
    },
  });

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(service: ServiceRead) {
    setEditing(service);
    setFormOpen(true);
  }

  return (
    <div>
      <PageHeader
        title="Servicos"
        description="Servicos oferecidos pelo seu negocio, usados como contexto pela IA."
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={openCreate}>
            Novo servico
          </Button>
        }
      />

      {isLoading ? (
        <PageSpinner />
      ) : !services || services.length === 0 ? (
        <EmptyState
          icon={Wrench}
          title="Nenhum servico cadastrado"
          description="Cadastre os servicos que o seu negocio oferece."
          action={<Button onClick={openCreate}>Cadastrar servico</Button>}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {services.map((service) => (
            <Card key={service.id}>
              <CardContent className="space-y-3 p-5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold text-foreground">{service.name}</p>
                    {service.category && <p className="text-xs text-foreground/45">{service.category}</p>}
                  </div>
                  <div className="flex gap-1">
                    <Button size="icon" variant="ghost" onClick={() => openEdit(service)} aria-label="Editar">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => setDeleting(service)}
                      aria-label="Excluir"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                {service.description && (
                  <p className="line-clamp-2 text-sm text-foreground/60">{service.description}</p>
                )}
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-brand-700">
                    {formatCurrency(service.price, service.currency)}
                  </span>
                  {service.duration_minutes && (
                    <span className="flex items-center gap-1 text-xs text-foreground/50">
                      <Clock className="h-3.5 w-3.5" /> {service.duration_minutes} min
                    </span>
                  )}
                </div>
                {service.deliverables.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {service.deliverables.map((item) => (
                      <span key={item} className="rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700">
                        {item}
                      </span>
                    ))}
                  </div>
                )}
                {!service.is_active && (
                  <span className="rounded-full bg-surface-muted px-2 py-0.5 text-xs text-foreground/50">
                    Inativo
                  </span>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <ServiceFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        service={editing}
        loading={createMutation.isPending || updateMutation.isPending}
        onSubmit={(values) => {
          const payload: ServicePayload = {
            ...values,
            description: values.description || null,
            category: values.category || null,
            price: values.price === "" || values.price === undefined ? null : Number(values.price),
            duration_minutes:
              values.duration_minutes === "" || values.duration_minutes === undefined
                ? null
                : Number(values.duration_minutes),
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
        title="Remover servico"
        description={`Tem certeza que deseja remover "${deleting?.name}"?`}
        confirmLabel="Remover"
        danger
        loading={removeMutation.isPending}
      />
    </div>
  );
}

function ServiceFormDialog({
  open,
  onClose,
  service,
  onSubmit,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  service: ServiceRead | null;
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
    defaultValues: { name: "", currency: "BRL", deliverables: [], is_active: true },
  });

  useEffect(() => {
    if (open) {
      reset(
        service
          ? {
              name: service.name,
              description: service.description ?? "",
              category: service.category ?? "",
              price: service.price !== null ? String(service.price) : "",
              currency: service.currency,
              duration_minutes:
                service.duration_minutes !== null ? String(service.duration_minutes) : "",
              deliverables: service.deliverables,
              is_active: service.is_active,
            }
          : {
              name: "",
              description: "",
              category: "",
              price: "",
              currency: "BRL",
              duration_minutes: "",
              deliverables: [],
              is_active: true,
            }
      );
    }
  }, [open, service, reset]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={service ? "Editar servico" : "Novo servico"}
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
          <Label htmlFor="s_name">Nome</Label>
          <Input id="s_name" {...register("name")} />
          <FieldError>{errors.name?.message}</FieldError>
        </div>
        <div>
          <Label htmlFor="s_description">Descricao</Label>
          <Textarea id="s_description" rows={3} {...register("description")} />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label htmlFor="s_category">Categoria</Label>
            <Input id="s_category" {...register("category")} />
          </div>
          <div>
            <Label htmlFor="s_price">Preco</Label>
            <Input id="s_price" type="number" step="0.01" min={0} {...register("price")} />
          </div>
          <div>
            <Label htmlFor="s_duration">Duracao (min)</Label>
            <Input id="s_duration" type="number" min={1} {...register("duration_minutes")} />
          </div>
        </div>
        <div>
          <Label>Entregaveis</Label>
          <Controller
            control={control}
            name="deliverables"
            render={({ field }) => (
              <TagInput value={field.value} onChange={field.onChange} placeholder="Ex.: Relatorio final" />
            )}
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-foreground/70">
          <input type="checkbox" className="h-4 w-4 rounded" {...register("is_active")} />
          Servico ativo
        </label>
      </form>
    </Dialog>
  );
}
