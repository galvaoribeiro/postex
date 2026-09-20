"use client";

import { Check, Copy, Download, RefreshCw } from "lucide-react";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { DestinationBadge, OUTPUT_META } from "@/components/domain/destination-badge";
import { ContentStatusBadge } from "@/components/domain/status-badge";
import type { ReelPayload } from "@/components/domain/payload-editor";
import { Button } from "@/components/ui/button";
import type { CampaignOutput, CampaignRead, ContentRead, JobStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type Tab = "IMAGE" | "VIDEO" | "COPY";

export function CampaignPreview({
  campaign,
  actions,
  onRegenerate,
  regenerating,
  className,
}: {
  campaign: CampaignRead;
  actions?: ReactNode;
  onRegenerate?: (output: CampaignOutput) => void;
  regenerating?: CampaignOutput | null;
  className?: string;
}) {
  const content = campaign.contents[0] ?? null;
  const available = (["IMAGE", "VIDEO", "COPY"] as Tab[]).filter((tab) =>
    campaign.outputs_requested.includes(tab)
  );
  const [tab, setTab] = useState<Tab>(available[0] ?? "COPY");

  return (
    <div className={cn("flex flex-col items-center gap-6", className)}>
      <div className="w-full max-w-md space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">{campaign.title}</h2>
            <p className="mt-1 text-sm text-foreground/55">
              {campaign.product?.name ?? "Produto"} · campanha pronta para exportar
            </p>
          </div>
          <DestinationBadge destination={campaign.destination} />
        </div>
        {campaign.failed_outputs.length > 0 && (
          <p className="rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Nao foi possivel gerar: {campaign.failed_outputs.join(", ")}. Regenere essa saida.
          </p>
        )}
        <div className="flex gap-2">
          {available.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setTab(item)}
              className={cn(
                "flex-1 rounded-xl border px-3 py-2 text-sm font-medium",
                tab === item
                  ? "border-brand-500 bg-brand-50 text-brand-800"
                  : "border-border-subtle text-foreground/65"
              )}
            >
              {OUTPUT_META[item].label}
            </button>
          ))}
        </div>
        {content && tab === "IMAGE" && (
          <ImagePane content={content} onRegenerate={onRegenerate} regenerating={regenerating} />
        )}
        {content && tab === "VIDEO" && (
          <VideoPane content={content} onRegenerate={onRegenerate} regenerating={regenerating} />
        )}
        {content && tab === "COPY" && (
          <CopyPane
            content={content}
            destination={campaign.destination}
            onRegenerate={onRegenerate}
            regenerating={regenerating}
          />
        )}
      </div>
      {actions && <div className="flex w-full max-w-md flex-wrap justify-center gap-2">{actions}</div>}
    </div>
  );
}

function ImagePane({
  content,
  onRegenerate,
  regenerating,
}: {
  content: ContentRead;
  onRegenerate?: (output: CampaignOutput) => void;
  regenerating?: CampaignOutput | null;
}) {
  const cover =
    content.assets.find((link) => link.role === "COVER" && link.asset.url)?.asset ??
    content.assets.find((link) => link.asset.mime_type.startsWith("image/") && link.asset.url)?.asset;
  return (
    <div className="space-y-3">
      <PhoneFrame>
        {cover?.url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={cover.url} alt={cover.alt_text ?? ""} className="aspect-[9/16] w-full object-cover" />
        ) : (
          <div className="flex aspect-[9/16] items-center justify-center bg-zinc-100 text-sm text-zinc-500">
            Imagem ainda nao gerada
          </div>
        )}
      </PhoneFrame>
      <ArtifactActions
        downloadUrl={cover?.url ?? null}
        downloadName={cover?.original_filename}
        onRegenerate={onRegenerate ? () => onRegenerate("IMAGE") : undefined}
        regenerating={regenerating === "IMAGE"}
      />
    </div>
  );
}

function VideoPane({
  content,
  onRegenerate,
  regenerating,
}: {
  content: ContentRead;
  onRegenerate?: (output: CampaignOutput) => void;
  regenerating?: CampaignOutput | null;
}) {
  const video = content.assets.find((link) => link.role === "PRIMARY_VIDEO" && link.asset.url)?.asset;
  const thumb = content.assets.find((link) => link.role === "THUMBNAIL" && link.asset.url)?.asset;
  const payload = content.payload as unknown as ReelPayload;
  return (
    <div className="space-y-3">
      <PhoneFrame>
        {video?.url ? (
          <video
            className="aspect-[9/16] w-full bg-black object-cover"
            controls
            playsInline
            poster={thumb?.url ?? undefined}
            src={video.url}
          />
        ) : (
          <div className="flex aspect-[9/16] items-center justify-center bg-zinc-900 text-sm text-white/70">
            Video ainda nao gerado
          </div>
        )}
      </PhoneFrame>
      {payload?.hook && (
        <p className="rounded-xl bg-zinc-900 px-3 py-2 text-sm text-white">{payload.hook}</p>
      )}
      <ArtifactActions
        downloadUrl={video?.url ?? null}
        downloadName={video?.original_filename}
        onRegenerate={onRegenerate ? () => onRegenerate("VIDEO") : undefined}
        regenerating={regenerating === "VIDEO"}
      />
    </div>
  );
}

function CopyPane({
  content,
  destination,
  onRegenerate,
  regenerating,
}: {
  content: ContentRead;
  destination: CampaignRead["destination"];
  onRegenerate?: (output: CampaignOutput) => void;
  regenerating?: CampaignOutput | null;
}) {
  const payload = content.payload as unknown as ReelPayload;
  const text = [
    content.caption,
    content.cta ? `CTA: ${content.cta}` : "",
    content.hashtags.map((tag) => (tag.startsWith("#") ? tag : `#${tag}`)).join(" "),
  ]
    .filter(Boolean)
    .join("\n\n");

  return (
    <div className="space-y-3 rounded-2xl border border-border-subtle bg-surface p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-foreground">{content.title}</p>
        <ContentStatusBadge status={content.status} />
      </div>
      {payload?.hook && (
        <blockquote className="rounded-xl bg-zinc-900 px-3 py-2 text-sm text-white">
          {payload.hook}
        </blockquote>
      )}
      {content.caption && (
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/80">{content.caption}</p>
      )}
      {content.hashtags.length > 0 && (
        <p className="text-sm text-brand-700">
          {content.hashtags.map((tag) => (tag.startsWith("#") ? tag : `#${tag}`)).join(" ")}
        </p>
      )}
      {content.cta && (
        <div className="rounded-xl bg-brand-50 px-3 py-2 text-center text-sm font-semibold text-brand-800">
          {content.cta}
        </div>
      )}
      {payload?.scenes && payload.scenes.length > 0 && (
        <div className="space-y-2 border-t border-border-subtle pt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-foreground/45">Roteiro</p>
          {payload.scenes.map((scene, index) => (
            <div key={index} className="rounded-xl bg-surface-muted px-3 py-2 text-sm">
              <p className="text-[11px] font-semibold uppercase text-foreground/40">
                Cena {scene.order ?? index + 1}
                {scene.duration_seconds ? ` · ${scene.duration_seconds}s` : ""}
              </p>
              {scene.voiceover && <p className="mt-1 text-foreground/80">{scene.voiceover}</p>}
            </div>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          icon={<Copy className="h-4 w-4" />}
          onClick={() => {
            void navigator.clipboard.writeText(text);
            toast.success(`Copy de ${destination === "INSTAGRAM" ? "Instagram" : "TikTok"} copiada.`);
          }}
        >
          Copiar
        </Button>
        {onRegenerate && (
          <Button
            variant="ghost"
            size="sm"
            icon={<RefreshCw className="h-4 w-4" />}
            loading={regenerating === "COPY"}
            onClick={() => onRegenerate("COPY")}
          >
            Regenerar copy
          </Button>
        )}
      </div>
    </div>
  );
}

function PhoneFrame({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-[2.2rem] border-[10px] border-zinc-900 bg-zinc-900 shadow-2xl shadow-black/30">
      <div className="overflow-hidden rounded-[1.45rem] bg-black">{children}</div>
    </div>
  );
}

function ArtifactActions({
  downloadUrl,
  downloadName,
  onRegenerate,
  regenerating,
}: {
  downloadUrl: string | null;
  downloadName?: string | null;
  onRegenerate?: () => void;
  regenerating?: boolean;
}) {
  return (
    <div className="flex flex-wrap justify-center gap-2">
      {downloadUrl && (
        <Button
          variant="outline"
          size="sm"
          icon={<Download className="h-4 w-4" />}
          onClick={() => downloadFile(downloadUrl, downloadName ?? "arquivo")}
        >
          Baixar
        </Button>
      )}
      {onRegenerate && (
        <Button
          variant="ghost"
          size="sm"
          icon={<RefreshCw className="h-4 w-4" />}
          loading={regenerating}
          onClick={onRegenerate}
        >
          Regenerar
        </Button>
      )}
    </div>
  );
}

function downloadFile(url: string, filename: string) {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  link.target = "_blank";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

export function StageChecklist({
  stage,
  status,
  outputs,
}: {
  stage: string | null;
  status: JobStatus;
  outputs?: CampaignOutput[];
}) {
  const steps = [
    { key: "analise", label: "Analise" },
    { key: "copy", label: "Copy" },
    ...(outputs?.includes("IMAGE") || !outputs ? [{ key: "imagem", label: "Imagem" }] : []),
    ...(outputs?.includes("VIDEO") ? [{ key: "video", label: "Video" }] : []),
    { key: "finalizando", label: "Finalizando" },
  ];
  const order = steps.map((step) => step.key);
  const currentIndex =
    status === "COMPLETED" ? order.length : stage ? order.indexOf(stage) : -1;

  return (
    <ol className="space-y-3">
      {steps.map((step, index) => {
        const done = status === "COMPLETED" || (currentIndex >= 0 && index < currentIndex);
        const current = status !== "COMPLETED" && index === currentIndex;
        return (
          <li key={step.key} className="flex items-center gap-3">
            <span
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-full border text-xs font-semibold",
                done && "border-success-fg bg-success-bg text-success-fg",
                current && "border-brand-500 bg-brand-50 text-brand-700",
                !done && !current && "border-border-subtle text-foreground/35"
              )}
            >
              {done ? <Check className="h-3.5 w-3.5" /> : index + 1}
            </span>
            <span
              className={cn(
                "text-sm font-medium",
                done && "text-success-fg",
                current && "text-foreground",
                !done && !current && "text-foreground/40"
              )}
            >
              {step.label}
              {current && status === "PROCESSING" ? "…" : ""}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
