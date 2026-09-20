import { Image as ImageIcon, ShoppingBag, Video } from "lucide-react";

import { cn } from "@/lib/utils";
import type { CampaignDestination } from "@/lib/api/types";

export const DESTINATION_META: Record<
  CampaignDestination,
  { label: string; className: string }
> = {
  INSTAGRAM: { label: "Instagram", className: "bg-fuchsia-50 text-fuchsia-800" },
  TIKTOK: { label: "TikTok", className: "bg-zinc-900 text-white" },
  TIKTOK_SHOP: { label: "TikTok Shop", className: "bg-rose-50 text-rose-800" },
};

export function DestinationBadge({
  destination,
  className,
}: {
  destination: CampaignDestination;
  className?: string;
}) {
  const meta = DESTINATION_META[destination];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
        meta.className,
        className
      )}
    >
      {meta.label}
    </span>
  );
}

export const OUTPUT_META = {
  IMAGE: { label: "Imagem", icon: ImageIcon },
  VIDEO: { label: "Video", icon: Video },
  COPY: { label: "Copy", icon: ShoppingBag },
} as const;
