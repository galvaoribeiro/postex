"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FieldError, Input, Label, Textarea } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { Progress } from "@/components/ui/progress";
import { TagInput } from "@/components/ui/tag-input";
import { useBusiness, useUpdateBusiness } from "@/lib/hooks/use-business";

const profileSchema = z.object({
  name: z.string().min(2).max(160),
  segment: z.string().min(2).max(120),
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

type ProfileValues = z.infer<typeof profileSchema>;

export default function BusinessSettingsPage() {
  const { data: business, isLoading } = useBusiness();

  if (isLoading || !business) {
    return <PageSpinner label="Carregando negocio..." />;
  }

  return (
    <div>
      <PageHeader
        title="Meu Negocio"
        description="Essas informacoes viram contexto comercial para as campanhas de produto."
      />

      <Card className="mb-6">
        <CardContent className="p-5">
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="font-medium text-foreground">Completude do perfil</span>
            <span className="text-foreground/55">{business.completeness_score}%</span>
          </div>
          <Progress value={business.completeness_score} />
          <p className="mt-2 text-xs text-foreground/50">
            Quanto mais completo, mais especificas ficam as campanhas geradas a partir dos seus produtos.
          </p>
        </CardContent>
      </Card>

      <ProfileForm business={business} />
    </div>
  );
}

function ProfileForm({ business }: { business: NonNullable<ReturnType<typeof useBusiness>["data"]> }) {
  const update = useUpdateBusiness();
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isDirty },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      name: business.name,
      segment: business.segment,
      description: business.description ?? "",
      target_audience: business.target_audience ?? "",
      location: business.location ?? "",
      brand_voice: business.brand_voice ?? "",
      additional_info: business.additional_info ?? "",
      instagram_handle: business.instagram_handle ?? "",
      website: business.website ?? "",
      differentiators: business.differentiators,
      objectives: business.objectives,
    },
  });

  useEffect(() => {
    reset({
      name: business.name,
      segment: business.segment,
      description: business.description ?? "",
      target_audience: business.target_audience ?? "",
      location: business.location ?? "",
      brand_voice: business.brand_voice ?? "",
      additional_info: business.additional_info ?? "",
      instagram_handle: business.instagram_handle ?? "",
      website: business.website ?? "",
      differentiators: business.differentiators,
      objectives: business.objectives,
    });
  }, [business, reset]);

  function onSubmit(values: ProfileValues) {
    update.mutate({
      ...values,
      description: values.description || null,
      target_audience: values.target_audience || null,
      location: values.location || null,
      brand_voice: values.brand_voice || null,
      additional_info: values.additional_info || null,
      instagram_handle: values.instagram_handle || null,
      website: values.website || null,
    });
  }

  return (
    <Card>
      <CardContent className="space-y-5 p-6">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="name">Nome do negocio</Label>
              <Input id="name" {...register("name")} />
              <FieldError>{errors.name?.message}</FieldError>
            </div>
            <div>
              <Label htmlFor="segment">Segmento</Label>
              <Input id="segment" {...register("segment")} />
              <FieldError>{errors.segment?.message}</FieldError>
            </div>
          </div>

          <div>
            <Label htmlFor="description">Descricao</Label>
            <Textarea id="description" rows={3} {...register("description")} />
          </div>

          <div>
            <Label htmlFor="target_audience">Publico-alvo</Label>
            <Textarea id="target_audience" rows={2} {...register("target_audience")} />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="location">Localizacao</Label>
              <Input id="location" {...register("location")} />
            </div>
            <div>
              <Label htmlFor="instagram_handle">Instagram (@)</Label>
              <Input id="instagram_handle" {...register("instagram_handle")} />
            </div>
          </div>

          <div>
            <Label htmlFor="website">Site</Label>
            <Input id="website" {...register("website")} />
          </div>

          <div>
            <Label htmlFor="brand_voice">Tom de comunicacao</Label>
            <Textarea id="brand_voice" rows={2} {...register("brand_voice")} />
          </div>

          <div>
            <Label>Diferenciais</Label>
            <Controller
              control={control}
              name="differentiators"
              render={({ field }) => <TagInput value={field.value} onChange={field.onChange} />}
            />
          </div>

          <div>
            <Label>Objetivos comerciais</Label>
            <Controller
              control={control}
              name="objectives"
              render={({ field }) => <TagInput value={field.value} onChange={field.onChange} />}
            />
          </div>

          <div>
            <Label htmlFor="additional_info">Informacoes adicionais</Label>
            <Textarea id="additional_info" rows={2} {...register("additional_info")} />
          </div>

          <div className="flex justify-end">
            <Button type="submit" loading={update.isPending} disabled={!isDirty}>
              Salvar alteracoes
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
