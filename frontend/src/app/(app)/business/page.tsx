"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FieldError, Input, Label, Textarea } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { Progress } from "@/components/ui/progress";
import { Select } from "@/components/ui/select";
import { TagInput } from "@/components/ui/tag-input";
import { aiApi } from "@/lib/api/ai";
import type { ContentFormat } from "@/lib/api/types";
import { useBusiness, useUpdateBusiness } from "@/lib/hooks/use-business";
import { queryKeys } from "@/lib/query-keys";
import { cn } from "@/lib/utils";

const FORMATS: { value: ContentFormat; label: string }[] = [
  { value: "REEL", label: "Reel" },
  { value: "IMAGE_POST", label: "Post" },
  { value: "CAROUSEL", label: "Carrossel" },
  { value: "STORY", label: "Story" },
];

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
  const [tab, setTab] = useState<"profile" | "preferences">("profile");

  if (isLoading || !business) {
    return <PageSpinner label="Carregando negocio..." />;
  }

  return (
    <div>
      <PageHeader
        title="Meu Negocio"
        description="Essas informacoes sao a base do contexto que a IA usa para gerar ideias e conteudos."
      />

      <Card className="mb-6">
        <CardContent className="p-5">
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="font-medium text-foreground">Completude do perfil</span>
            <span className="text-foreground/55">{business.completeness_score}%</span>
          </div>
          <Progress value={business.completeness_score} />
          <p className="mt-2 text-xs text-foreground/50">
            Quanto mais completo, mais especificas ficam as ideias geradas pelo Motor de Conteudo.
          </p>
        </CardContent>
      </Card>

      <div className="mb-6 flex gap-2 rounded-xl bg-surface-muted p-1">
        <TabButton active={tab === "profile"} onClick={() => setTab("profile")}>
          Perfil do negocio
        </TabButton>
        <TabButton active={tab === "preferences"} onClick={() => setTab("preferences")}>
          Preferencias de conteudo
        </TabButton>
      </div>

      {tab === "profile" ? <ProfileForm business={business} /> : <PreferencesForm business={business} />}
    </div>
  );
}

function TabButton({
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
        "flex-1 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
        active ? "bg-surface text-brand-700 shadow-sm" : "text-foreground/55 hover:text-foreground"
      )}
    >
      {children}
    </button>
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
            <Label>Objetivos com o Instagram</Label>
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

function PreferencesForm({ business }: { business: NonNullable<ReturnType<typeof useBusiness>["data"]> }) {
  const update = useUpdateBusiness();
  const { data: taxonomy } = useQuery({ queryKey: queryKeys.taxonomy, queryFn: aiApi.taxonomy });

  const [preferredFormats, setPreferredFormats] = useState<ContentFormat[]>(
    business.content_preferences.preferred_formats as ContentFormat[]
  );
  const [preferredCategories, setPreferredCategories] = useState<string[]>(
    business.content_preferences.preferred_categories
  );
  const [avoidedCategories, setAvoidedCategories] = useState<string[]>(
    business.content_preferences.avoided_categories
  );
  const [postsPerWeek, setPostsPerWeek] = useState(business.content_preferences.posts_per_week);
  const [emojiUsage, setEmojiUsage] = useState(business.content_preferences.emoji_usage);
  const [forbiddenTopics, setForbiddenTopics] = useState<string[]>(
    business.content_preferences.forbidden_topics
  );
  const [extraGuidelines, setExtraGuidelines] = useState(business.content_preferences.extra_guidelines);

  function toggleFormat(format: ContentFormat) {
    setPreferredFormats((prev) =>
      prev.includes(format) ? prev.filter((f) => f !== format) : [...prev, format]
    );
  }

  function toggleCategory(key: string, list: "preferred" | "avoided") {
    if (list === "preferred") {
      setPreferredCategories((prev) =>
        prev.includes(key) ? prev.filter((c) => c !== key) : [...prev, key]
      );
      setAvoidedCategories((prev) => prev.filter((c) => c !== key));
    } else {
      setAvoidedCategories((prev) => (prev.includes(key) ? prev.filter((c) => c !== key) : [...prev, key]));
      setPreferredCategories((prev) => prev.filter((c) => c !== key));
    }
  }

  function handleSave() {
    update.mutate({
      content_preferences: {
        preferred_formats: preferredFormats,
        preferred_categories: preferredCategories,
        avoided_categories: avoidedCategories,
        posts_per_week: postsPerWeek,
        language: business.content_preferences.language,
        emoji_usage: emojiUsage,
        forbidden_topics: forbiddenTopics,
        extra_guidelines: extraGuidelines,
      },
    });
  }

  return (
    <Card>
      <CardContent className="space-y-6 p-6">
        <div>
          <Label>Formatos preferidos</Label>
          <div className="flex flex-wrap gap-2">
            {FORMATS.map((format) => (
              <button
                key={format.value}
                type="button"
                onClick={() => toggleFormat(format.value)}
                className={cn(
                  "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                  preferredFormats.includes(format.value)
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-border-subtle text-foreground/55 hover:border-brand-200"
                )}
              >
                {format.label}
              </button>
            ))}
          </div>
        </div>

        {taxonomy && (
          <div>
            <Label>Pilares editoriais</Label>
            <p className="mb-2 text-xs text-foreground/50">
              Marque como preferido para priorizar, ou como evitar para reduzir a frequencia.
            </p>
            <div className="space-y-2">
              {taxonomy.categories.map((category) => (
                <div
                  key={category.key}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border-subtle p-3"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground">{category.label}</p>
                    <p className="text-xs text-foreground/50">{category.description}</p>
                  </div>
                  <div className="flex shrink-0 gap-1.5">
                    <button
                      type="button"
                      onClick={() => toggleCategory(category.key, "preferred")}
                      className={cn(
                        "rounded-full px-2.5 py-1 text-xs font-medium",
                        preferredCategories.includes(category.key)
                          ? "bg-success-bg text-success-fg"
                          : "bg-surface-muted text-foreground/50 hover:text-foreground"
                      )}
                    >
                      Preferido
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleCategory(category.key, "avoided")}
                      className={cn(
                        "rounded-full px-2.5 py-1 text-xs font-medium",
                        avoidedCategories.includes(category.key)
                          ? "bg-danger-bg text-danger-fg"
                          : "bg-surface-muted text-foreground/50 hover:text-foreground"
                      )}
                    >
                      Evitar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="posts_per_week">Posts por semana (meta)</Label>
            <Input
              id="posts_per_week"
              type="number"
              min={1}
              max={21}
              value={postsPerWeek}
              onChange={(event) => setPostsPerWeek(Number(event.target.value))}
            />
          </div>
          <div>
            <Label htmlFor="emoji_usage">Uso de emojis</Label>
            <Select
              id="emoji_usage"
              value={emojiUsage}
              onChange={(event) => setEmojiUsage(event.target.value)}
            >
              <option value="nenhum">Nenhum</option>
              <option value="moderado">Moderado</option>
              <option value="frequente">Frequente</option>
            </Select>
          </div>
        </div>

        <div>
          <Label>Temas proibidos</Label>
          <TagInput value={forbiddenTopics} onChange={setForbiddenTopics} placeholder="Ex.: politica" />
        </div>

        <div>
          <Label htmlFor="extra_guidelines">Diretrizes adicionais para a IA</Label>
          <Textarea
            id="extra_guidelines"
            rows={3}
            value={extraGuidelines}
            onChange={(event) => setExtraGuidelines(event.target.value)}
            placeholder="Ex.: Sempre mencionar horario de funcionamento nos posts de produto."
          />
        </div>

        <div className="flex justify-end">
          <Button onClick={handleSave} loading={update.isPending}>
            Salvar preferencias
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
