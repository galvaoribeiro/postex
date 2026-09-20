"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus, Tag } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { DestinationBadge } from "@/components/domain/destination-badge";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { PageSpinner } from "@/components/ui/spinner";
import { campaignsApi } from "@/lib/api/campaigns";
import { dashboardApi } from "@/lib/api/dashboard";
import type { CampaignDestination, CampaignSummary, QuickCreateItem } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";
import { cn, formatCurrency } from "@/lib/utils";

const DESTINATIONS: { value: CampaignDestination; label: string; description: string }[] = [
  { value: "INSTAGRAM", label: "Instagram", description: "Imagem + copy para o feed." },
  { value: "TIKTOK", label: "TikTok", description: "Video vertical + roteiro." },
  { value: "TIKTOK_SHOP", label: "TikTok Shop", description: "Video comercial com CTA de compra." },
];

export default function InicioPage() {
  const router = useRouter();
  const [item, setItem] = useState<QuickCreateItem | null>(null);
  const [destination, setDestination] = useState<CampaignDestination | null>(null);

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

  function handleCreate() {
    if (!item) {
      toast.error("Escolha um produto ou cadastre um novo.");
      return;
    }
    if (!destination) {
      toast.error("Escolha onde publicar.");
      return;
    }
    const params = new URLSearchParams({ destination, product: item.id });
    router.push(`/criar?${params.toString()}`);
  }

  const waiting = campaignsQuery.data?.items ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        title={`Ola, ${data.business_name}`}
        description="Transforme um produto em conteudo que vende. Sem precisar saber o que postar."
      />

      <section>
        <h2 className="text-sm font-semibold text-foreground">Qual produto vamos vender?</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <Chip active={false} icon={<Plus className="h-3.5 w-3.5" />} onClick={() => router.push("/criar")}>
            Novo produto
          </Chip>
          {(data.quick_create ?? [])
            .filter((entry) => entry.kind === "product")
            .map((entry) => (
              <Chip
                key={entry.id}
                active={item?.id === entry.id}
                icon={<Tag className="h-3.5 w-3.5" />}
                onClick={() => setItem(entry)}
              >
                {entry.name}
                {entry.price != null ? ` · ${formatCurrency(entry.price)}` : ""}
              </Chip>
            ))}
        </div>
        {(data.quick_create ?? []).length === 0 && (
          <p className="mt-3 text-sm text-foreground/45">
            Ainda nao ha produto cadastrado. Use Novo produto para comecar.
          </p>
        )}

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {DESTINATIONS.map((entry) => (
            <button
              key={entry.value}
              type="button"
              onClick={() => setDestination(entry.value)}
              className={cn(
                "rounded-2xl border px-4 py-4 text-left transition-colors",
                destination === entry.value
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
          Gerar campanha
        </Button>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-foreground">Esperando voce</h2>
        <p className="mt-1 text-sm text-foreground/55">Revise, exporte e publique onde quiser.</p>
        <div className="mt-3 space-y-2">
          {waiting.length === 0 ? (
            <p className="rounded-xl bg-surface-muted px-4 py-6 text-center text-sm text-foreground/45">
              Nenhuma campanha aguardando. Gere a proxima.
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
