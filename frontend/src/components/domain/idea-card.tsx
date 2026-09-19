"use client";

import { Sparkles, Trash2, Wand2 } from "lucide-react";

import { FormatBadge } from "@/components/domain/format-badge";
import { IdeaStatusBadge } from "@/components/domain/status-badge";
import { Button } from "@/components/ui/button";
import type { ContentIdeaRead } from "@/lib/api/types";

export function IdeaCard({
  idea,
  onUse,
  onDiscard,
  onDelete,
  busy,
}: {
  idea: ContentIdeaRead;
  onUse?: (idea: ContentIdeaRead) => void;
  onDiscard?: (idea: ContentIdeaRead) => void;
  onDelete?: (idea: ContentIdeaRead) => void;
  busy?: boolean;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border-subtle bg-surface p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <FormatBadge format={idea.suggested_format} />
          <span className="rounded-full bg-surface-muted px-2 py-1 text-xs font-medium text-foreground/60">
            {idea.category}
          </span>
        </div>
        <IdeaStatusBadge status={idea.status} />
      </div>

      <div>
        <p className="font-semibold text-foreground">{idea.title}</p>
        <p className="mt-1 text-sm text-foreground/60">{idea.concept}</p>
      </div>

      {idea.hook_suggestion && (
        <p className="flex items-start gap-1.5 rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-700">
          <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {idea.hook_suggestion}
        </p>
      )}

      <div className="flex items-center justify-between text-xs text-foreground/45">
        <span>Relevancia: {idea.relevance_score}/100</span>
        {(idea.referenced_products.length > 0 || idea.referenced_services.length > 0) && (
          <span className="truncate">
            {[...idea.referenced_products, ...idea.referenced_services].join(", ")}
          </span>
        )}
      </div>

      {idea.status === "AVAILABLE" && (onUse || onDiscard || onDelete) && (
        <div className="flex flex-wrap gap-2 border-t border-border-subtle pt-3">
          {onUse && (
            <Button size="sm" icon={<Wand2 className="h-4 w-4" />} onClick={() => onUse(idea)} disabled={busy}>
              Transformar em conteudo
            </Button>
          )}
          {onDiscard && (
            <Button size="sm" variant="outline" onClick={() => onDiscard(idea)} disabled={busy}>
              Descartar
            </Button>
          )}
          {onDelete && (
            <Button
              size="icon"
              variant="ghost"
              onClick={() => onDelete(idea)}
              disabled={busy}
              aria-label="Excluir ideia"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
