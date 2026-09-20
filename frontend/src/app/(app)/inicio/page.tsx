"use client";

import { useQuery } from "@tanstack/react-query";
import { Sparkles, Store, Tag } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { ContentSummaryItem } from "@/components/domain/content-summary-item";
import { FORMAT_META } from "@/components/domain/format-badge";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageSpinner } from "@/components/ui/spinner";
import { dashboardApi } from "@/lib/api/dashboard";
import type { ContentObjective, QuickCreateItem } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";
import { addDays, cn, formatCurrency, startOfWeekMonday, toIsoDate } from "@/lib/utils";

const OBJECTIVES: { value: ContentObjective; label: string; description: string }[] = [
  { value: "SELL", label: "Vender", description: "Convencer a pessoa a comprar." },
  { value: "ATTRACT", label: "Atrair clientes", description: "Trazer gente nova para o perfil." },
  { value: "BRAND", label: "Fortalecer a marca", description: "Mostrar quem voce e." },
];

const WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"];

export default function InicioPage() {
  const router = useRouter();
  const today = new Date();
  const weekStart = startOfWeekMonday(today);
  const weekEnd = addDays(weekStart, 6);

  const [item, setItem] = useState<QuickCreateItem | null>(null);
  const [brandOnly, setBrandOnly] = useState(true);
  const [objective, setObjective] = useState<ContentObjective | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: dashboardApi.get,
    refetchInterval: 30_000,
  });

  const months = [
    { year: weekStart.getFullYear(), month: weekStart.getMonth() + 1 },
    { year: weekEnd.getFullYear(), month: weekEnd.getMonth() + 1 },
  ].filter(
    (value, index, list) =>
      list.findIndex((entry) => entry.year === value.year && entry.month === value.month) === index
  );

  const weekQuery = useQuery({
    queryKey: queryKeys.calendar(weekStart.getFullYear(), weekStart.getMonth() + 1),
    queryFn: () => dashboardApi.calendar(weekStart.getFullYear(), weekStart.getMonth() + 1),
  });
  const extraMonth = months[1];
  const extraQuery = useQuery({
    queryKey: extraMonth
      ? queryKeys.calendar(extraMonth.year, extraMonth.month)
      : ["calendar", "skip"],
    queryFn: () => dashboardApi.calendar(extraMonth!.year, extraMonth!.month),
    enabled: Boolean(extraMonth),
  });

  if (isLoading || !data) {
    return <PageSpinner label="Carregando..." />;
  }

  const daysByDate = new Map(
    [...(weekQuery.data?.days ?? []), ...(extraQuery.data?.days ?? [])].map((day) => [
      day.day,
      day.contents,
    ])
  );

  function selectItem(next: QuickCreateItem) {
    setItem(next);
    setBrandOnly(false);
  }

  function handleCreate() {
    if (!objective) {
      toast.error("Escolha um objetivo.");
      return;
    }
    if (objective === "SELL" && !item) {
      toast.error("Para vender, escolha um produto ou servico.");
      return;
    }
    const params = new URLSearchParams({ objective });
    if (item && !brandOnly) {
      params.set(item.kind === "product" ? "product" : "service", item.id);
    }
    router.push(`/criar?${params.toString()}`);
  }

  const waiting = data.in_review;

  return (
    <div className="space-y-8">
      <PageHeader
        title={`Ola, ${data.business_name}`}
        description="Escolha o que divulgar. O pedido completo acontece em Criar."
      />

      <section>
        <h2 className="text-sm font-semibold text-foreground">O que vamos divulgar hoje?</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <Chip
            active={brandOnly}
            icon={<Sparkles className="h-3.5 w-3.5" />}
            onClick={() => {
              setBrandOnly(true);
              setItem(null);
            }}
          >
            So a marca
          </Chip>
          {(data.quick_create ?? []).map((entry) => (
            <Chip
              key={entry.id}
              active={item?.id === entry.id}
              icon={
                entry.kind === "product" ? (
                  <Tag className="h-3.5 w-3.5" />
                ) : (
                  <Store className="h-3.5 w-3.5" />
                )
              }
              onClick={() => selectItem(entry)}
            >
              {entry.name}
              {entry.price != null ? ` · ${formatCurrency(entry.price)}` : ""}
            </Chip>
          ))}
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {OBJECTIVES.map((entry) => (
            <button
              key={entry.value}
              type="button"
              onClick={() => setObjective(entry.value)}
              className={cn(
                "rounded-2xl border px-4 py-4 text-left transition-colors",
                objective === entry.value
                  ? "border-brand-500 bg-brand-50"
                  : "border-border-subtle bg-surface hover:border-brand-200"
              )}
            >
              <p className="font-semibold text-foreground">{entry.label}</p>
              <p className="mt-1 text-xs text-foreground/55">{entry.description}</p>
            </button>
          ))}
        </div>

        <Button className="mt-4" size="lg" onClick={handleCreate}>
          Criar conteudo
        </Button>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-foreground">Esperando voce</h2>
        <p className="mt-1 text-sm text-foreground/55">Abra o preview. Aprovar nao e as cegas.</p>
        <div className="mt-3 space-y-2">
          {waiting.length === 0 ? (
            <p className="rounded-xl bg-surface-muted px-4 py-6 text-center text-sm text-foreground/45">
              Nada esperando revisao. Crie o proximo post.
            </p>
          ) : (
            waiting.map((content) => <ContentSummaryItem key={content.id} content={content} />)
          )}
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-foreground">Esta semana</h2>
        <div className="mt-3 grid grid-cols-7 gap-1">
          {WEEKDAYS.map((label, index) => {
            const date = addDays(weekStart, index);
            const key = toIsoDate(date);
            const contents = daysByDate.get(key) ?? [];
            const isToday = key === toIsoDate(today);
            return (
              <Card
                key={key}
                className={cn("min-h-[88px]", isToday && "border-brand-400 bg-brand-50/40")}
              >
                <CardContent className="p-2">
                  <p className="text-[11px] font-medium text-foreground/45">{label}</p>
                  <p className={cn("text-sm font-semibold", isToday && "text-brand-700")}>
                    {date.getDate()}
                  </p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {contents.map((content) => {
                      const Icon = FORMAT_META[content.format].icon;
                      return (
                        <span
                          key={content.id}
                          title={content.title}
                          className={cn(
                            "inline-flex h-6 w-6 items-center justify-center rounded-md",
                            FORMAT_META[content.format].className
                          )}
                        >
                          <Icon className="h-3.5 w-3.5" />
                        </span>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function Chip({
  active,
  icon,
  onClick,
  children,
}: {
  active: boolean;
  icon: ReactNode;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition-colors",
        active
          ? "border-brand-500 bg-brand-50 text-brand-800"
          : "border-border-subtle text-foreground/70 hover:border-brand-200"
      )}
    >
      {icon}
      {children}
    </button>
  );
}
