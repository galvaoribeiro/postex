import { Clapperboard, GalleryHorizontalEnd, Image as ImageIcon, PlayCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import type { ContentFormat } from "@/lib/api/types";

export const FORMAT_META: Record<
  ContentFormat,
  { label: string; icon: typeof Clapperboard; className: string }
> = {
  REEL: { label: "Reel", icon: Clapperboard, className: "bg-purple-50 text-purple-700" },
  IMAGE_POST: { label: "Post", icon: ImageIcon, className: "bg-sky-50 text-sky-700" },
  CAROUSEL: {
    label: "Carrossel",
    icon: GalleryHorizontalEnd,
    className: "bg-amber-50 text-amber-700",
  },
  STORY: { label: "Story", icon: PlayCircle, className: "bg-rose-50 text-rose-700" },
};

export function FormatBadge({ format, className }: { format: ContentFormat; className?: string }) {
  const meta = FORMAT_META[format];
  const Icon = meta.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        meta.className,
        className
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {meta.label}
    </span>
  );
}
