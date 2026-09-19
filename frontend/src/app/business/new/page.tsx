"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Building2, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { FieldError, Input, Label, Textarea } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { TagInput } from "@/components/ui/tag-input";
import { PageSpinner } from "@/components/ui/spinner";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { aiApi } from "@/lib/api/ai";
import { businessApi } from "@/lib/api/business";
import { ApiError } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";
import { useSession } from "@/lib/hooks/use-session";

const schema = z.object({
  name: z.string().min(2, "Informe o nome do negocio.").max(160),
  segment: z.string().min(2, "Informe o segmento.").max(120),
  description: z.string().max(4000).optional().or(z.literal("")),
  target_audience: z.string().max(2000).optional().or(z.literal("")),
  location: z.string().max(180).optional().or(z.literal("")),
  brand_voice: z.string().max(1000).optional().or(z.literal("")),
  additional_info: z.string().max(4000).optional().or(z.literal("")),
  instagram_handle: z.string().max(80).optional().or(z.literal("")),
  website: z.string().max(255).optional().or(z.literal("")),
  differentiators: z.array(z.string()),
  objectives: z.array(z.string()),
});

type FormValues = z.infer<typeof schema>;

export default function BusinessOnboardingPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: session, isLoading: sessionLoading } = useSession();

  const { data: taxonomy } = useQuery({
    queryKey: queryKeys.taxonomy,
    queryFn: aiApi.taxonomy,
  });

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      segment: "",
      description: "",
      target_audience: "",
      location: "",
      brand_voice: "",
      additional_info: "",
      instagram_handle: "",
      website: "",
      differentiators: [],
      objectives: [],
    },
  });

  useEffect(() => {
    if (!sessionLoading && session?.has_business) {
      router.replace("/dashboard");
    }
  }, [sessionLoading, session, router]);

  const create = useMutation({
    mutationFn: businessApi.create,
    onSuccess: (business) => {
      queryClient.setQueryData(queryKeys.business, business);
      queryClient.invalidateQueries({ queryKey: queryKeys.session });
      toast.success(`Negocio "${business.name}" criado! Vamos gerar suas primeiras ideias.`);
      router.push("/dashboard");
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : "Nao foi possivel salvar o negocio.");
    },
  });

  if (sessionLoading || !session) {
    return <PageSpinner label="Carregando..." />;
  }

  function onSubmit(values: FormValues) {
    create.mutate({
      name: values.name,
      segment: values.segment,
      description: values.description || null,
      target_audience: values.target_audience || null,
      location: values.location || null,
      brand_voice: values.brand_voice || null,
      additional_info: values.additional_info || null,
      instagram_handle: values.instagram_handle || null,
      website: values.website || null,
      differentiators: values.differentiators,
      objectives: values.objectives,
    });
  }

  return (
    <div className="min-h-screen bg-background px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-lg shadow-brand-600/30">
            <Building2 className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-semibold text-foreground">Conte sobre o seu negocio</h1>
          <p className="mt-2 text-sm text-foreground/55">
            Essas informacoes alimentam o Motor de Conteudo: quanto mais contexto, mais especificas e
            relevantes ficam as ideias e os conteudos gerados para o seu Instagram.
          </p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-6 rounded-2xl border border-border-subtle bg-surface p-6 shadow-sm sm:p-8"
        >
          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-brand-600">
              O essencial
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="name">Nome do negocio *</Label>
                <Input id="name" placeholder="Ex.: Cafeteria Aroma" {...register("name")} />
                <FieldError>{errors.name?.message}</FieldError>
              </div>
              <div>
                <Label htmlFor="segment">Segmento *</Label>
                <Input id="segment" placeholder="Ex.: Cafeteria e confeitaria" {...register("segment")} />
                <FieldError>{errors.segment?.message}</FieldError>
              </div>
            </div>
            <div>
              <Label htmlFor="description">Descricao do negocio</Label>
              <Textarea
                id="description"
                rows={3}
                placeholder="O que voce vende, como trabalha, o que te torna diferente..."
                {...register("description")}
              />
            </div>
          </section>

          <section className="space-y-4 border-t border-border-subtle pt-6">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-brand-600">
              Publico e localizacao
            </h2>
            <div>
              <Label htmlFor="target_audience">Publico-alvo</Label>
              <Textarea
                id="target_audience"
                rows={2}
                placeholder="Quem compra de voce? Idade, interesses, comportamento..."
                {...register("target_audience")}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="location">Localizacao</Label>
                <Input id="location" placeholder="Cidade, bairro ou regiao" {...register("location")} />
              </div>
              <div>
                <Label htmlFor="instagram_handle">Instagram (@)</Label>
                <Input id="instagram_handle" placeholder="@seunegocio" {...register("instagram_handle")} />
              </div>
            </div>
            <div>
              <Label htmlFor="website">Site (opcional)</Label>
              <Input id="website" placeholder="https://" {...register("website")} />
            </div>
          </section>

          <section className="space-y-4 border-t border-border-subtle pt-6">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-brand-600">
              Voz e diferenciais
            </h2>
            <div>
              <Label htmlFor="brand_voice">Tom de comunicacao</Label>
              <Textarea
                id="brand_voice"
                rows={2}
                placeholder="Ex.: Proximo e acolhedor, com humor leve, sem formalidade excessiva."
                {...register("brand_voice")}
              />
            </div>
            <div>
              <Label>Diferenciais</Label>
              <Controller
                control={control}
                name="differentiators"
                render={({ field }) => (
                  <TagInput value={field.value} onChange={field.onChange} placeholder="Ex.: Cafe 100% especial" />
                )}
              />
            </div>
            <div>
              <Label>Objetivos com o Instagram</Label>
              <Controller
                control={control}
                name="objectives"
                render={({ field }) => (
                  <TagInput
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="Ex.: Atrair clientes locais"
                  />
                )}
              />
            </div>
            <div>
              <Label htmlFor="additional_info">Informacoes adicionais</Label>
              <Textarea
                id="additional_info"
                rows={2}
                placeholder="Qualquer outro contexto util para a IA"
                {...register("additional_info")}
              />
            </div>
          </section>

          {taxonomy && (
            <section className="rounded-xl bg-surface-muted p-4 text-xs text-foreground/60">
              O Motor de Conteudo ja vem configurado com {taxonomy.categories.length} pilares editoriais
              (educativo, prova social, bastidores e mais). Voce podera ajustar as preferencias em
              Configuracoes apos criar o negocio.
            </section>
          )}

          <Button type="submit" size="lg" className="w-full" loading={create.isPending}>
            {create.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Criando negocio...
              </>
            ) : (
              "Criar negocio e comecar"
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}
