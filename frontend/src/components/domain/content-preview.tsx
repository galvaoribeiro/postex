"use client";

import { Check } from "lucide-react";
import type { ReactNode } from "react";

import {
  FORMAT_META,
  FormatBadge,
} from "@/components/domain/format-badge";
import type {
  CarouselPayload,
  ImagePostPayload,
  ReelPayload,
  StoryPayload,
} from "@/components/domain/payload-editor";
import { ContentStatusBadge } from "@/components/domain/status-badge";
import type { ContentRead } from "@/lib/api/types";
import { cn } from "@/lib/utils";

/**
 * Preview no formato de celular: roteiro, legendas e CTA.
 * Nao e um player de video — o MVP mostra o que sera publicado, como storyboard.
 */
export function ContentPreview({
  content,
  actions,
  className,
}: {
  content: ContentRead;
  actions?: ReactNode;
  className?: string;
}) {
  const cover = content.assets.find((link) => link.role === "COVER" && link.asset.url)?.asset.url
    ?? content.assets.find((link) => link.asset.url)?.asset.url
    ?? null;

  return (
    <div className={cn("flex flex-col items-center gap-6", className)}>
      <div className="w-full max-w-[340px]">
        <div className="rounded-[2.2rem] border-[10px] border-zinc-900 bg-zinc-900 shadow-2xl shadow-black/30">
          <div className="relative overflow-hidden rounded-[1.45rem] bg-white">
            <div className="flex justify-center bg-zinc-900 pb-2 pt-3">
              <div className="h-5 w-24 rounded-full bg-zinc-800" />
            </div>
            <div className="max-h-[560px] overflow-y-auto scrollbar-thin">
              {cover ? (
                <div className="relative">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={cover} alt="" className="aspect-[4/5] w-full object-cover" />
                </div>
              ) : (
                <div className="flex h-28 items-end bg-gradient-to-br from-brand-700 to-brand-400 px-4 pb-3">
                  <FormatBadge format={content.format} className="bg-white/90" />
                </div>
              )}
              <div className="space-y-4 p-4">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-[15px] font-semibold leading-snug text-zinc-900">
                    {content.title}
                  </h2>
                  <ContentStatusBadge status={content.status} />
                </div>
                <PreviewBody content={content} />
                {(content.caption || content.cta || content.hashtags.length > 0) && (
                  <div className="space-y-2 border-t border-zinc-100 pt-3">
                    {content.caption && (
                      <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-zinc-700">
                        {content.caption}
                      </p>
                    )}
                    {content.hashtags.length > 0 && (
                      <p className="text-[12px] leading-relaxed text-brand-700">
                        {content.hashtags.map((tag) =>
                          tag.startsWith("#") ? tag : `#${tag}`
                        ).join(" ")}
                      </p>
                    )}
                    {content.cta && (
                      <div className="rounded-xl bg-brand-50 px-3 py-2 text-center text-[13px] font-semibold text-brand-800">
                        {content.cta}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
            <div className="flex justify-center bg-white py-2">
              <div className="h-1.5 w-28 rounded-full bg-zinc-300" />
            </div>
          </div>
        </div>
        <p className="mt-3 text-center text-xs text-foreground/45">
          Preview da peca · exporte os arquivos para publicar
        </p>
      </div>
      {actions && <div className="flex w-full max-w-md flex-wrap justify-center gap-2">{actions}</div>}
    </div>
  );
}

function PreviewBody({ content }: { content: ContentRead }) {
  const payload = content.payload ?? {};
  switch (content.format) {
    case "REEL":
      return <ReelStoryboard payload={payload as unknown as ReelPayload} />;
    case "IMAGE_POST":
      return <ImagePostBoard payload={payload as unknown as ImagePostPayload} />;
    case "CAROUSEL":
      return <CarouselBoard payload={payload as unknown as CarouselPayload} />;
    case "STORY":
      return <StoryBoard payload={payload as unknown as StoryPayload} />;
    default:
      return content.concept ? (
        <p className="text-[13px] text-zinc-600">{content.concept}</p>
      ) : null;
  }
}

function ReelStoryboard({ payload }: { payload: ReelPayload }) {
  const scenes = payload.scenes ?? [];
  return (
    <div className="space-y-3">
      {payload.hook && (
        <blockquote className="rounded-xl bg-zinc-900 px-3 py-2.5 text-[13px] font-medium leading-snug text-white">
          {payload.hook}
        </blockquote>
      )}
      <ol className="space-y-2">
        {scenes.map((scene, index) => (
          <li key={index} className="rounded-xl border border-zinc-100 bg-zinc-50 p-3">
            <div className="mb-1 flex items-center justify-between text-[11px] font-semibold uppercase tracking-wide text-zinc-400">
              <span>Cena {scene.order ?? index + 1}</span>
              {scene.duration_seconds ? <span>{scene.duration_seconds}s</span> : null}
            </div>
            {scene.visual && <p className="text-[13px] text-zinc-800">{scene.visual}</p>}
            {scene.on_screen_text && (
              <p className="mt-1 text-[12px] font-medium text-brand-700">“{scene.on_screen_text}”</p>
            )}
            {scene.voiceover && (
              <p className="mt-1 text-[12px] italic text-zinc-500">{scene.voiceover}</p>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

function ImagePostBoard({ payload }: { payload: ImagePostPayload }) {
  return (
    <div className="space-y-3">
      {payload.headline && (
        <p className="text-lg font-semibold leading-snug text-zinc-900">{payload.headline}</p>
      )}
      {payload.on_image_text && (
        <p className="rounded-lg bg-zinc-900 px-3 py-2 text-center text-sm font-medium text-white">
          {payload.on_image_text}
        </p>
      )}
      {payload.body_text && (
        <p className="text-[13px] leading-relaxed text-zinc-600">{payload.body_text}</p>
      )}
      {payload.visual_direction && (
        <p className="text-[12px] text-zinc-400">Direcao visual: {payload.visual_direction}</p>
      )}
    </div>
  );
}

function CarouselBoard({ payload }: { payload: CarouselPayload }) {
  const slides = payload.slides ?? [];
  return (
    <div className="space-y-2">
      {payload.cover_title && (
        <p className="rounded-xl bg-brand-600 px-3 py-3 text-sm font-semibold text-white">
          {payload.cover_title}
        </p>
      )}
      {slides.map((slide, index) => (
        <div key={index} className="rounded-xl border border-zinc-100 px-3 py-2.5">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-400">
            Slide {slide.order ?? index + 1}
          </p>
          {slide.title && <p className="mt-0.5 text-[13px] font-semibold text-zinc-900">{slide.title}</p>}
          {slide.body && <p className="mt-1 text-[12px] text-zinc-600">{slide.body}</p>}
        </div>
      ))}
    </div>
  );
}

function StoryBoard({ payload }: { payload: StoryPayload }) {
  const frames = payload.frames ?? [];
  return (
    <ol className="space-y-2">
      {frames.map((frame, index) => (
        <li key={index} className="rounded-xl border border-zinc-100 bg-zinc-50 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-400">
            Frame {frame.order ?? index + 1}
          </p>
          {frame.visual && <p className="mt-1 text-[13px] text-zinc-800">{frame.visual}</p>}
          {frame.text && <p className="mt-1 text-[13px] font-medium text-zinc-900">{frame.text}</p>}
          {frame.interaction && (
            <p className="mt-1 text-[12px] text-brand-700">{frame.interaction}</p>
          )}
        </li>
      ))}
    </ol>
  );
}

export function StageChecklist({
  stage,
  status,
}: {
  stage: string | null;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
}) {
  const steps = [
    { key: "ideia", label: "Ideia" },
    { key: "roteiro", label: "Roteiro" },
    { key: "imagem", label: "Imagem" },
    { key: "finalizando", label: "Finalizando" },
  ] as const;
  const order = steps.map((step) => step.key);
  const currentIndex =
    status === "COMPLETED" ? order.length : stage ? order.indexOf(stage as (typeof order)[number]) : -1;

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
