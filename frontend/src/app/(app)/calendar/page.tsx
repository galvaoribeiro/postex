"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Clock } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { FormatBadge } from "@/components/domain/format-badge";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input, Label } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api/client";
import { contentsApi } from "@/lib/api/contents";
import { dashboardApi } from "@/lib/api/dashboard";
import type { ContentSummary } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";
import { cn } from "@/lib/utils";

const WEEKDAYS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"];
const MONTH_NAMES = [
  "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

export default function CalendarPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [scheduling, setScheduling] = useState<ContentSummary | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.calendar(year, month),
    queryFn: () => dashboardApi.calendar(year, month),
  });

  function goPrev() {
    if (month === 1) {
      setMonth(12);
      setYear((y) => y - 1);
    } else {
      setMonth((m) => m - 1);
    }
  }

  function goNext() {
    if (month === 12) {
      setMonth(1);
      setYear((y) => y + 1);
    } else {
      setMonth((m) => m + 1);
    }
  }

  const scheduleMutation = useMutation({
    mutationFn: ({ id, date }: { id: string; date: string }) => contentsApi.schedule(id, date),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendar"] });
      toast.success("Conteudo agendado.");
      setScheduling(null);
    },
    onError: (error: unknown) => toast.error(error instanceof ApiError ? error.message : "Erro ao agendar."),
  });

  const firstDay = new Date(year, month - 1, 1);
  const leadingBlanks = firstDay.getDay();
  const daysInMonth = data?.days ?? [];

  return (
    <div>
      <PageHeader
        title="Calendario"
        description="Visualize e organize o que sera publicado."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={goPrev} aria-label="Mes anterior">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="w-40 text-center text-sm font-medium text-foreground">
              {MONTH_NAMES[month - 1]} {year}
            </span>
            <Button variant="outline" size="icon" onClick={goNext} aria-label="Proximo mes">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        }
      />

      {isLoading || !data ? (
        <PageSpinner />
      ) : (
        <div className="grid gap-6 lg:grid-cols-4">
          <Card className="lg:col-span-3">
            <CardContent className="p-4">
              <div className="mb-2 grid grid-cols-7 gap-1 text-center text-xs font-medium text-foreground/45">
                {WEEKDAYS.map((day) => (
                  <span key={day}>{day}</span>
                ))}
              </div>
              <div className="grid grid-cols-7 gap-1">
                {Array.from({ length: leadingBlanks }).map((_, index) => (
                  <div key={`blank-${index}`} className="min-h-[92px] rounded-lg bg-transparent" />
                ))}
                {daysInMonth.map((day) => {
                  const dateNum = Number(day.day.slice(-2));
                  const isToday = day.day === today.toISOString().slice(0, 10);
                  return (
                    <div
                      key={day.day}
                      className={cn(
                        "min-h-[92px] rounded-lg border border-border-subtle p-1.5",
                        isToday && "border-brand-400 bg-brand-50/40"
                      )}
                    >
                      <span className={cn("text-xs font-medium", isToday ? "text-brand-700" : "text-foreground/50")}>
                        {dateNum}
                      </span>
                      <div className="mt-1 space-y-1">
                        {day.contents.slice(0, 3).map((content) => (
                          <Link
                            key={content.id}
                            href={`/contents/${content.id}`}
                            className="block truncate rounded bg-surface-muted px-1.5 py-0.5 text-[11px] text-foreground/70 hover:bg-brand-50 hover:text-brand-700"
                            title={content.title}
                          >
                            {content.title}
                          </Link>
                        ))}
                        {day.contents.length > 3 && (
                          <span className="block text-[10px] text-foreground/40">
                            +{day.contents.length - 3} mais
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-foreground">
                <Clock className="h-4 w-4 text-brand-600" /> Sem data definida
              </h3>
              {data.unscheduled.length === 0 ? (
                <p className="rounded-xl bg-surface-muted px-3 py-6 text-center text-xs text-foreground/45">
                  Tudo com data planejada.
                </p>
              ) : (
                <div className="space-y-2">
                  {data.unscheduled.map((content) => (
                    <div key={content.id} className="rounded-xl border border-border-subtle p-2.5">
                      <Link href={`/contents/${content.id}`} className="text-sm font-medium text-foreground hover:text-brand-700">
                        {content.title}
                      </Link>
                      <div className="mt-1 flex items-center justify-between">
                        <FormatBadge format={content.format} />
                        <Button size="sm" variant="outline" onClick={() => setScheduling(content)}>
                          Agendar
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <ScheduleDialog
        content={scheduling}
        onClose={() => setScheduling(null)}
        onConfirm={(date) => scheduling && scheduleMutation.mutate({ id: scheduling.id, date })}
        loading={scheduleMutation.isPending}
      />
    </div>
  );
}

function ScheduleDialog({
  content,
  onClose,
  onConfirm,
  loading,
}: {
  content: ContentSummary | null;
  onClose: () => void;
  onConfirm: (date: string) => void;
  loading: boolean;
}) {
  const [date, setDate] = useState("");

  return (
    <Dialog
      open={Boolean(content)}
      onClose={onClose}
      title={`Agendar "${content?.title ?? ""}"`}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={() => date && onConfirm(date)} loading={loading} disabled={!date}>
            Confirmar
          </Button>
        </>
      }
    >
      <Label htmlFor="schedule_date">Data planejada</Label>
      <Input id="schedule_date" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
    </Dialog>
  );
}
