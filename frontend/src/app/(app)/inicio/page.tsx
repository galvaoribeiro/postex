"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { DestinationBadge } from "@/components/domain/destination-badge";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { PageSpinner } from "@/components/ui/spinner";
import { campaignsApi } from "@/lib/api/campaigns";
import { dashboardApi } from "@/lib/api/dashboard";
import type { CampaignSummary } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";

export default function InicioPage() {
  const router = useRouter();
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: dashboardApi.get,
    refetchInterval: 30_000,
  });
  const campaignsQuery = useQuery({
    queryKey: queryKeys.campaigns({ status: ["REVIEW", "GENERATING"] }),
    queryFn: () => campaignsApi.list({ status: ["REVIEW", "GENERATING"], limit: 8 }),
  });

  if (isLoading) {
    return <PageSpinner label="Carregando..." />;
  }

  if (isError || !data) {
    return (
      <div className="flex min-h-64 flex-col items-center justify-center gap-4 px-6 text-center">
        <p className="text-sm text-foreground/70">
          Nao foi possivel carregar o inicio. Confira a API e tente de novo.
        </p>
        <Button onClick={() => void refetch()} loading={isFetching}>
          Tentar novamente
        </Button>
      </div>
    );
  }

  const waiting = campaignsQuery.data?.items ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        title={`Ola, ${data.business_name}`}
        description="Transforme um produto em conteudo que vende. Sem precisar saber o que postar."
        actions={
          <Button onClick={() => router.push("/criar")}>Gerar campanha</Button>
        }
      />

      <section>
        <h2 className="text-sm font-semibold text-foreground">Esperando voce</h2>
        <p className="mt-1 text-sm text-foreground/55">Revise, exporte e publique onde quiser.</p>
        <div className="mt-3 space-y-2">
          {waiting.length === 0 ? (
            <p className="rounded-xl bg-surface-muted px-4 py-6 text-center text-sm text-foreground/45">
              Nenhuma campanha aguardando. Gere a proxima em Criar.
            </p>
          ) : (
            waiting.map((campaign) => <CampaignRow key={campaign.id} campaign={campaign} />)
          )}
        </div>
      </section>
    </div>
  );
}

function CampaignRow({ campaign }: { campaign: CampaignSummary }) {
  return (
    <a
      href={`/contents/${campaign.id}`}
      className="flex items-center justify-between gap-3 rounded-xl border border-border-subtle bg-surface px-4 py-3 transition-colors hover:border-brand-200 hover:bg-brand-50/40"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-foreground">{campaign.title}</p>
        <p className="mt-1 text-xs text-foreground/50">{campaign.product_name}</p>
      </div>
      <DestinationBadge destination={campaign.destination} />
    </a>
  );
}
