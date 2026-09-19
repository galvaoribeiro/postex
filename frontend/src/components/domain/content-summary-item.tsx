import Link from "next/link";

import { ContentStatusBadge } from "@/components/domain/status-badge";
import { FormatBadge } from "@/components/domain/format-badge";
import type { ContentSummary } from "@/lib/api/types";
import { formatRelativeDay } from "@/lib/utils";

export function ContentSummaryItem({ content }: { content: ContentSummary }) {
  return (
    <Link
      href={`/contents/${content.id}`}
      className="flex items-center justify-between gap-3 rounded-xl border border-border-subtle bg-surface px-4 py-3 transition-colors hover:border-brand-200 hover:bg-brand-50/40"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-foreground">{content.title}</p>
        <div className="mt-1 flex items-center gap-2 text-xs text-foreground/50">
          <FormatBadge format={content.format} />
          {content.category && <span>{content.category}</span>}
        </div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1.5">
        <ContentStatusBadge status={content.status} />
        {content.planned_date && (
          <span className="text-xs text-foreground/45">{formatRelativeDay(content.planned_date)}</span>
        )}
      </div>
    </Link>
  );
}
