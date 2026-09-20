"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { CampaignPreview } from "@/components/domain/campaign-preview";
import { Button } from "@/components/ui/button";
import { PageSpinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api/client";
import { campaignsApi } from "@/lib/api/campaigns";
import type { CampaignOutput } from "@/lib/api/types";
import { useJobWatcher } from "@/lib/hooks/use-job-watcher";
import { queryKeys } from "@/lib/query-keys";

export default function CampaignDetailPage() {
  const params = useParams<{ id: string }>();
  const campaignId = params.id;
  const queryClient = useQueryClient();
  const { watch } = useJobWatcher();
  const [regenerating, setRegenerating] = useState<CampaignOutput | null>(null);

  const { data: campaign, isLoading } = useQuery({
    queryKey: queryKeys.campaign(campaignId),
    queryFn: () => campaignsApi.get(campaignId),
  });

  const approveMutation = useMutation({
    mutationFn: () => campaignsApi.approve(campaignId),
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.campaign(campaignId), updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.campaigns() });
      toast.success("Campanha aprovada.");
    },
    onError: (err: unknown) =>
      toast.error(err instanceof ApiError ? err.message : "Nao foi possivel aprovar."),
  });

  if (isLoading || !campaign) {
    return <PageSpinner label="Carregando campanha..." />;
  }

  async function handleRegenerate(output: CampaignOutput) {
    setRegenerating(output);
    try {
      const accepted = await campaignsApi.regenerate(campaignId, { output });
      const job = await watch(accepted.job_id, accepted.kind, {
        successMessage: "Saida regenerada.",
      });
      if (job?.status === "COMPLETED") {
        await queryClient.invalidateQueries({ queryKey: queryKeys.campaign(campaignId) });
      }
    } finally {
      setRegenerating(null);
    }
  }

  return (
    <div className="space-y-6">
      <Link
        href="/contents"
        className="inline-flex items-center gap-1.5 text-sm text-foreground/55 hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Campanhas
      </Link>
      <CampaignPreview
        campaign={campaign}
        onRegenerate={(output) => void handleRegenerate(output)}
        regenerating={regenerating}
        actions={
          <>
            <Button
              icon={<Check className="h-4 w-4" />}
              onClick={() => approveMutation.mutate()}
              loading={approveMutation.isPending}
              disabled={campaign.status === "APPROVED"}
            >
              {campaign.status === "APPROVED" ? "Aprovada" : "Aprovar"}
            </Button>
            <Button
              variant="outline"
              icon={<RefreshCw className="h-4 w-4" />}
              onClick={() => void handleRegenerate("COPY")}
              loading={regenerating === "COPY"}
            >
              Regenerar copy
            </Button>
          </>
        }
      />
    </div>
  );
}
