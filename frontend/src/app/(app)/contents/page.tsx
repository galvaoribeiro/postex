"use client";

import { useQuery } from "@tanstack/react-query";
import { Notebook, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { StageChecklist } from "@/components/domain/campaign-preview";
import { DESTINATION_META, DestinationBadge, OUTPUT_META } from "@/components/domain/destination-badge";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { campaignsApi } from "@/lib/api/campaigns";
import { jobsApi } from "@/lib/api/jobs";
import type { CampaignDestination, CampaignOutput, CampaignStatus, JobRead } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";
import { cn, formatDate } from "@/lib/utils";

type Tab = "creating" | "review" | "approved" | "failed";

const TABS: { id: Tab; label: string }[] = [
  { id: "creating", label: "Em criacao" },
  { id: "review", label: "Para revisar" },
  { id: "approved", label: "Aprovadas" },
  { id: "failed", label: "Falhas" },
];

const TAB_STATUSES: Record<Exclude<Tab, "creating">, CampaignStatus[]> = {
  review: ["REVIEW"],
  approved: ["APPROVED"],
  failed: ["FAILED"],
};

const DESTINATIONS: CampaignDestination[] = ["INSTAGRAM", "TIKTOK", "TIKTOK_SHOP"];
const OUTPUTS: CampaignOutput[] = ["IMAGE", "VIDEO", "COPY"];

export default function ContentsPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("review");
  const [search, setSearch] = useState("");
  const [destination, setDestination] = useState<CampaignDestination | "ALL">("ALL");
  const [output, setOutput] = useState<CampaignOutput | "ALL">("ALL");

  const jobsQuery = useQuery({
    queryKey: queryKeys.job("active-campaign"),
    queryFn: () => jobsApi.list({ kind: "CAMPAIGN_GENERATION", limit: 50 }),
    enabled: tab === "creating",
    refetchInterval: tab === "creating" ? 4000 : false,
  });
  const regenQuery = useQuery({
    queryKey: ["jobs", "campaign-regen"],
    queryFn: () => jobsApi.list({ kind: "CAMPAIGN_REGENERATION", limit: 50 }),
    enabled: tab === "creating",
    refetchInterval: tab === "creating" ? 4000 : false,
  });

  const listQuery = useQuery({
    queryKey: queryKeys.campaigns({ tab, search, destination }),
    queryFn: () =>
      campaignsApi.list({
        status: tab === "creating" ? undefined : TAB_STATUSES[tab],
        destination: destination === "ALL" ? undefined : [destination],
        search: search || undefined,
        limit: 100,
      }),
    enabled: tab !== "creating",
  });
  const campaigns =
    listQuery.data?.items.filter((item) =>
      output === "ALL" ? true : item.outputs_requested.includes(output)
    ) ?? [];

  const activeJobs = [...(jobsQuery.data ?? []), ...(regenQuery.data ?? [])].filter(
    (job, index, list) =>
      list.findIndex((item) => item.id === job.id) === index &&
      (job.status === "PENDING" || job.status === "PROCESSING")
  );

  return (
    <div>
      <PageHeader
        title="Campanhas"
        description="Do job em andamento a peca pronta para exportar."
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => router.push("/criar")}>
            Gerar campanha
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
                "rounded-full px-3 py-1.5 text-sm font-medium",
                tab === item.id
                  ? "bg-brand-600 text-white"
                  : "bg-surface-muted text-foreground/60 hover:text-foreground"
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
        {tab !== "creating" && (
          <div className="relative ml-auto w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground/40" />
            <Input
              className="pl-9"
              placeholder="Buscar campanha"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        )}
      </div>

      {tab !== "creating" && (
        <div className="mb-5 flex flex-wrap gap-2">
          <FilterChip active={destination === "ALL"} onClick={() => setDestination("ALL")}>
            Todos os destinos
          </FilterChip>
          {DESTINATIONS.map((item) => (
            <FilterChip
              key={item}
              active={destination === item}
              onClick={() => setDestination(item)}
            >
              {DESTINATION_META[item].label}
            </FilterChip>
          ))}
          <span className="mx-1 hidden h-6 w-px bg-border-subtle sm:inline-block" />
          <FilterChip active={output === "ALL"} onClick={() => setOutput("ALL")}>
            Todas as saidas
          </FilterChip>
          {OUTPUTS.map((item) => (
            <FilterChip key={item} active={output === item} onClick={() => setOutput(item)}>
              {OUTPUT_META[item].label}
            </FilterChip>
          ))}
        </div>
      )}

      {tab === "creating" && (
        <div className="space-y-3">
          {activeJobs.length === 0 ? (
            <EmptyState
              icon={Notebook}
              title="Nada em criacao"
              description="Gere uma campanha a partir de um produto."
            />
          ) : (
            activeJobs.map((job) => <ActiveJobCard key={job.id} job={job} />)
          )}
        </div>
      )}

      {tab !== "creating" && listQuery.isLoading && <PageSpinner label="Carregando campanhas..." />}
      {tab !== "creating" && listQuery.data && campaigns.length === 0 && (
        <EmptyState
          icon={Notebook}
          title="Nenhuma campanha aqui"
          description="Gere a primeira a partir de um produto."
        />
      )}
      {tab !== "creating" && listQuery.data && campaigns.length > 0 && (
        <div className="grid gap-3">
          {campaigns.map((campaign) => (
            <Link key={campaign.id} href={`/contents/${campaign.id}`}>
              <Card className="transition-colors hover:border-brand-200 hover:bg-brand-50/30">
                <CardContent className="flex items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-foreground">{campaign.title}</p>
                    <p className="mt-1 text-xs text-foreground/50">
                      {campaign.product_name} · {formatDate(campaign.updated_at)}
                    </p>
                  </div>
                  <DestinationBadge destination={campaign.destination} />
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
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
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
        active
          ? "border-brand-500 bg-brand-50 text-brand-800"
          : "border-border-subtle text-foreground/60 hover:border-brand-200"
      )}
    >
      {children}
    </button>
  );
}

function ActiveJobCard({ job }: { job: JobRead }) {
  const campaignId = typeof job.result?.campaign_id === "string" ? job.result.campaign_id : null;
  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-medium text-foreground">
            {job.kind === "CAMPAIGN_REGENERATION" ? "Regenerando campanha" : "Gerando campanha"}
          </p>
          <span className="text-xs text-foreground/45">{job.progress}%</span>
        </div>
        <StageChecklist stage={job.stage ?? null} status={job.status} />
        {campaignId && (
          <Link href={`/contents/${campaignId}`} className="text-sm font-medium text-brand-700">
            Abrir campanha
          </Link>
        )}
      </CardContent>
    </Card>
  );
}
