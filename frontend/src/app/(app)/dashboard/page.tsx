"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  CalendarCheck,
  Layers,
  Lightbulb,
  ListTodo,
  Loader2,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { ContentSummaryItem } from "@/components/domain/content-summary-item";
import { IdeaCard } from "@/components/domain/idea-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageSpinner } from "@/components/ui/spinner";
import { Progress } from "@/components/ui/progress";
import { PageHeader } from "@/components/layout/page-header";
import { dashboardApi } from "@/lib/api/dashboard";
import type { ContentSummary } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";

const NEXT_ACTION_HREF: Record<string, (nextAction: { content_id: string | null; idea_id: string | null }) => string> = {
  publish_today: (a) => `/contents/${a.content_id}`,
  review: (a) => `/contents/${a.content_id}`,
  pick_idea: () => "/ideas",
  generate_ideas: () => "/ideas",
  setup: () => "/business",
};

export default function DashboardPage() {
  const router = useRouter();
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: dashboardApi.get,
    refetchInterval: 30_000,
  });

  if (isLoading || !data) {
    return <PageSpinner label="Carregando o painel..." />;
  }

  const nextActionHref = NEXT_ACTION_HREF[data.next_action.kind]?.(data.next_action) ?? "/ideas";

  return (
    <div>
      <PageHeader
        title={`Ola, ${data.business_name}`}
        description="O que voce deve fazer hoje para manter o Instagram ativo."
      />

      <Card className="mb-6 overflow-hidden border-brand-200 bg-gradient-to-br from-brand-600 to-brand-800 text-white">
        <CardContent className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/15">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-white/70">Proxima acao</p>
              <p className="mt-0.5 text-lg font-semibold">{data.next_action.title}</p>
              <p className="mt-1 text-sm text-white/80">{data.next_action.description}</p>
            </div>
          </div>
          <Button
            variant="secondary"
            className="shrink-0 bg-white text-brand-700 hover:bg-white/90"
            onClick={() => router.push(nextActionHref)}
            icon={<ArrowRight className="h-4 w-4" />}
          >
            {data.next_action.cta_label}
          </Button>
        </CardContent>
      </Card>

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Layers} label="Conteudos" value={data.counters.total} hint={`${data.counters.created_last_30_days} nos ultimos 30 dias`} />
        <StatCard icon={Lightbulb} label="Ideias disponiveis" value={data.counters.ideas_available} hint="Prontas para produzir" />
        <StatCard icon={ListTodo} label="Em revisao" value={data.in_review.length} hint="Aguardando aprovacao" />
        <StatCard icon={Loader2} label="Processando" value={data.active_jobs} hint="Jobs de IA em andamento" spin={data.active_jobs > 0} />
      </div>

      <Card className="mb-6">
        <CardHeader>
          <div>
            <CardTitle className="flex items-center gap-2">
              <CalendarCheck className="h-4 w-4 text-brand-600" /> Cobertura do calendario
            </CardTitle>
          </div>
          <Link href="/calendar" className="text-sm font-medium text-brand-600 hover:underline">
            Ver calendario
          </Link>
        </CardHeader>
        <CardContent>
          <div className="mb-2 flex items-center justify-between text-sm text-foreground/60">
            <span>
              {data.calendar.scheduled_days} de {data.calendar.horizon_days} dias com conteudo agendado
            </span>
            <span className="font-medium text-foreground">{data.calendar.coverage_percent}%</span>
          </div>
          <Progress value={data.calendar.coverage_percent} />
          {data.calendar.next_gap_date && (
            <p className="mt-2 text-xs text-foreground/50">
              Proxima lacuna: {new Date(`${data.calendar.next_gap_date}T00:00:00`).toLocaleDateString("pt-BR")} - meta de{" "}
              {data.calendar.target_posts_per_week} posts/semana.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <ContentListCard title="Hoje" items={data.today} emptyLabel="Nada agendado para hoje." />
        <ContentListCard title="Em revisao" items={data.in_review} emptyLabel="Nada esperando revisao." />
        <ContentListCard title="Proximos" items={data.upcoming} emptyLabel="Nada agendado nos proximos dias." />
        <ContentListCard title="Recentes" items={data.recent} emptyLabel="Nenhum conteudo criado ainda." />
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="h-4 w-4 text-brand-600" /> Ideias em destaque
          </CardTitle>
          <Link href="/ideas" className="text-sm font-medium text-brand-600 hover:underline">
            Ver todas
          </Link>
        </CardHeader>
        <CardContent>
          {data.top_ideas.length === 0 ? (
            <EmptyState
              icon={Lightbulb}
              title="Ainda sem ideias"
              description="Gere as primeiras ideias com o Motor de Conteudo."
              action={
                <Button onClick={() => router.push("/ideas")}>Gerar ideias</Button>
              }
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {data.top_ideas.map((idea) => (
                <IdeaCard key={idea.id} idea={idea} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
  spin,
}: {
  icon: typeof Layers;
  label: string;
  value: number;
  hint?: string;
  spin?: boolean;
}) {
  return (
    <Card>
      <CardContent className="p-5 pt-5">
        <div className="flex items-center justify-between">
          <span className="text-sm text-foreground/55">{label}</span>
          <Icon className={`h-4 w-4 text-brand-500 ${spin ? "animate-spin" : ""}`} />
        </div>
        <p className="mt-2 text-2xl font-semibold text-foreground">{value}</p>
        {hint && <p className="mt-1 text-xs text-foreground/45">{hint}</p>}
      </CardContent>
    </Card>
  );
}

function ContentListCard({
  title,
  items,
  emptyLabel,
}: {
  title: string;
  items: ContentSummary[];
  emptyLabel: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {items.length === 0 ? (
          <p className="rounded-xl bg-surface-muted px-4 py-6 text-center text-sm text-foreground/45">
            {emptyLabel}
          </p>
        ) : (
          items.map((item) => <ContentSummaryItem key={item.id} content={item} />)
        )}
      </CardContent>
    </Card>
  );
}
