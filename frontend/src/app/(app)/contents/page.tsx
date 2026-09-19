"use client";

import { useQuery } from "@tanstack/react-query";
import { Notebook, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { FormatBadge } from "@/components/domain/format-badge";
import { StageChecklist } from "@/components/domain/content-preview";
import { ContentStatusBadge } from "@/components/domain/status-badge";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { contentsApi } from "@/lib/api/contents";
import { jobsApi } from "@/lib/api/jobs";
import type { ContentStatus, JobRead } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";
import { cn, formatDate } from "@/lib/utils";

type Tab = "creating" | "review" | "scheduled" | "published" | "archived";

const TABS: { id: Tab; label: string }[] = [
  { id: "creating", label: "Em criacao" },
  { id: "review", label: "Para aprovar" },
  { id: "scheduled", label: "Agendados" },
  { id: "published", label: "Publicados" },
];

const TAB_STATUSES: Record<Exclude<Tab, "creating">, ContentStatus[]> = {
  review: ["DRAFT", "REVIEW"],
  scheduled: ["SCHEDULED"],
  published: ["PUBLISHED"],
  archived: ["REJECTED", "ARCHIVED"],
};

export default function ContentsPage() {
  return <ContentsLibrary />;
}

function ContentsLibrary() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("review");
  const [search, setSearch] = useState("");

  const jobsQuery = useQuery({
    queryKey: queryKeys.job("active-creation"),
    queryFn: () => jobsApi.list({ kind: "CONTENT_CREATION", limit: 50 }),
    enabled: tab === "creating",
    refetchInterval: tab === "creating" ? 4000 : false,
  });
  const extraJobsQuery = useQuery({
    queryKey: ["jobs", "production-active"],
    queryFn: () => jobsApi.list({ limit: 50 }),
    enabled: tab === "creating",
    refetchInterval: tab === "creating" ? 4000 : false,
  });

  const listQuery = useQuery({
    queryKey: queryKeys.contents({ tab, search }),
    queryFn: () =>
      contentsApi.list({
        status: tab === "creating" ? undefined : TAB_STATUSES[tab],
        search: search || undefined,
        limit: 100,
      }),
    enabled: tab !== "creating",
  });

  const activeJobs = [...(jobsQuery.data ?? []), ...(extraJobsQuery.data ?? [])].filter(
    (job, index, list) =>
      list.findIndex((item) => item.id === job.id) === index &&
      (job.status === "PENDING" || job.status === "PROCESSING") &&
      (job.kind === "CONTENT_CREATION" ||
        job.kind === "CONTENT_PRODUCTION" ||
        job.kind === "CONTENT_REGENERATION")
  );

  return (
    <div>
      <PageHeader
        title="Conteudos"
        description="Do job em andamento ao post publicado."
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => router.push("/criar")}>
            Criar
          </Button>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-2">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                tab === item.id
                  ? "border-brand-500 bg-brand-50 text-brand-700"
                  : "border-border-subtle text-foreground/60 hover:border-brand-200"
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
        {tab !== "creating" && (
          <div className="relative min-w-[200px] flex-1 max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground/40" />
            <Input
              placeholder="Buscar por titulo..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="pl-9"
            />
          </div>
        )}
      </div>

      {tab === "creating" ? (
        jobsQuery.isLoading || extraJobsQuery.isLoading ? (
          <PageSpinner />
        ) : activeJobs.length === 0 ? (
          <EmptyState
            icon={Notebook}
            title="Nada em criacao"
            description="Quando um job estiver rodando, ele aparece aqui com as etapas."
            action={<Button onClick={() => router.push("/criar")}>Criar conteudo</Button>}
          />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {activeJobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )
      ) : listQuery.isLoading ? (
        <PageSpinner />
      ) : !listQuery.data || listQuery.data.items.length === 0 ? (
        <EmptyState
          icon={Notebook}
          title="Nenhum conteudo nesta aba"
          description="Crie um post em um passo a partir de um produto e um objetivo."
          action={<Button onClick={() => router.push("/criar")}>Criar conteudo</Button>}
        />
      ) : (
        <Card>
          <CardContent className="divide-y divide-border-subtle p-0">
            {listQuery.data.items.map((content) => (
              <Link
                key={content.id}
                href={`/contents/${content.id}`}
                className="flex items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-surface-muted/60"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-foreground">{content.title}</p>
                  <div className="mt-1 flex items-center gap-2 text-xs text-foreground/50">
                    {content.category && <span>{content.category}</span>}
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

      {tab !== "archived" && (
        <button
          type="button"
          onClick={() => setTab("archived")}
          className="mt-6 text-sm text-foreground/45 hover:text-foreground"
        >
          Arquivados
        </button>
      )}
    </div>
  );
}

function JobCard({ job }: { job: JobRead }) {
  const title = (job.result?.title as string | undefined) ?? "Criando conteudo";
  const contentId = job.result?.content_id as string | undefined;
  const inner = (
    <Card>
      <CardContent className="space-y-3 p-5 pt-5">
        <p className="font-medium text-foreground">{title}</p>
        <StageChecklist
          stage={job.stage ?? null}
          status={job.status === "PENDING" ? "PENDING" : job.status}
        />
      </CardContent>
    </Card>
  );
  if (!contentId) return inner;
  return <Link href={`/contents/${contentId}`}>{inner}</Link>;
}
