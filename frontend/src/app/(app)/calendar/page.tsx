"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Clock } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { FORMAT_META, FormatBadge } from "@/components/domain/format-badge";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input, Label } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api/client";
import { contentsApi } from "@/lib/api/contents";
import { dashboardApi } from "@/lib/api/dashboard";
import type { CalendarDay, ContentSummary } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";
import { addDays, cn, startOfWeekMonday, toIsoDate } from "@/lib/utils";

const WEEKDAYS_SUN = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"];
const WEEKDAYS_MON = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"];
const MONTH_NAMES = [
  "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

export default function CalendarPage() {
  const today = new Date();
  const [view, setView] = useState<"week" | "month">("week");
  const [weekStart, setWeekStart] = useState(() => startOfWeekMonday(today));
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [scheduling, setScheduling] = useState<ContentSummary | null>(null);
  const queryClient = useQueryClient();

  const weekEnd = addDays(weekStart, 6);
  const monthKeys = useMemo(() => {
    if (view === "month") return [{ year, month }];
    const start = { year: weekStart.getFullYear(), month: weekStart.getMonth() + 1 };
    const end = { year: weekEnd.getFullYear(), month: weekEnd.getMonth() + 1 };
    if (start.year === end.year && start.month === end.month) return [start];
    return [start, end];
  }, [view, year, month, weekStart, weekEnd]);

  const firstMonth = monthKeys[0];
  const secondMonth = monthKeys[1];
  const primary = useQuery({
    queryKey: queryKeys.calendar(firstMonth.year, firstMonth.month),
    queryFn: () => dashboardApi.calendar(firstMonth.year, firstMonth.month),
  });
  const secondary = useQuery({
    queryKey: secondMonth
      ? queryKeys.calendar(secondMonth.year, secondMonth.month)
      : ["calendar", "none"],
    queryFn: () => dashboardApi.calendar(secondMonth!.year, secondMonth!.month),
    enabled: Boolean(secondMonth),
  });

  function goPrev() {
    if (view === "week") {
      setWeekStart((current) => addDays(current, -7));
      return;
    }
    if (month === 1) {
      setMonth(12);
      setYear((value) => value - 1);
    } else {
      setMonth((value) => value - 1);
    }
  }

  function goNext() {
    if (view === "week") {
      setWeekStart((current) => addDays(current, 7));
      return;
    }
    if (month === 12) {
      setMonth(1);
      setYear((value) => value + 1);
    } else {
      setMonth((value) => value + 1);
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

  const daysByDate = new Map<string, CalendarDay["contents"]>(
    [...(primary.data?.days ?? []), ...(secondary.data?.days ?? [])].map((day) => [
      day.day,
      day.contents,
    ])
  );
  const unscheduled = primary.data?.unscheduled ?? [];
  const firstDay = new Date(year, month - 1, 1);
  const leadingBlanks = firstDay.getDay();
  const daysInMonth = primary.data?.days ?? [];
  const loading = primary.isLoading || (Boolean(secondMonth) && secondary.isLoading);

  const headerLabel =
    view === "week"
      ? `${weekStart.getDate()} ${MONTH_NAMES[weekStart.getMonth()].slice(0, 3)} – ${weekEnd.getDate()} ${MONTH_NAMES[weekEnd.getMonth()].slice(0, 3)} ${weekEnd.getFullYear()}`
      : `${MONTH_NAMES[month - 1]} ${year}`;

  return (
    <div>
      <PageHeader
        title="Calendario"
        description="Semana como visao padrao. Alterne para o mes se precisar do panorama."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex rounded-lg border border-border-subtle p-0.5">
              <button
                type="button"
                onClick={() => setView("week")}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm font-medium",
                  view === "week" ? "bg-brand-50 text-brand-700" : "text-foreground/60"
                )}
              >
                Semana
              </button>
              <button
                type="button"
                onClick={() => setView("month")}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm font-medium",
                  view === "month" ? "bg-brand-50 text-brand-700" : "text-foreground/60"
                )}
              >
                Mes
              </button>
            </div>
            <Button variant="outline" size="icon" onClick={goPrev} aria-label="Anterior">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="min-w-40 text-center text-sm font-medium text-foreground">{headerLabel}</span>
            <Button variant="outline" size="icon" onClick={goNext} aria-label="Proximo">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        }
      />

      {loading || !primary.data ? (
        <PageSpinner />
      ) : (
        <div className="grid gap-6 lg:grid-cols-4">
          <Card className="lg:col-span-3">
            <CardContent className="p-4">
              {view === "week" ? (
                <div className="grid grid-cols-7 gap-2">
                  {WEEKDAYS_MON.map((label, index) => {
                    const date = addDays(weekStart, index);
                    const key = toIsoDate(date);
                    const contents = daysByDate.get(key) ?? [];
                    const isToday = key === toIsoDate(today);
                    return (
                      <div
                        key={key}
                        className={cn(
                          "min-h-[140px] rounded-xl border border-border-subtle p-2",
                          isToday && "border-brand-400 bg-brand-50/40"
                        )}
                      >
                        <p className="text-[11px] font-medium text-foreground/45">{label}</p>
                        <p className={cn("text-sm font-semibold", isToday && "text-brand-700")}>
                          {date.getDate()}
                        </p>
                        <div className="mt-2 space-y-1">
                          {contents.map((content) => {
                            const Icon = FORMAT_META[content.format].icon;
                            return (
                              <Link
                                key={content.id}
                                href={`/contents/${content.id}`}
                                title={content.title}
                                className={cn(
                                  "flex items-center gap-1 truncate rounded-md px-1.5 py-1 text-[11px]",
                                  FORMAT_META[content.format].className
                                )}
                              >
                                <Icon className="h-3 w-3 shrink-0" />
                                <span className="truncate">{content.title}</span>
                              </Link>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <>
                  <div className="mb-2 grid grid-cols-7 gap-1 text-center text-xs font-medium text-foreground/45">
                    {WEEKDAYS_SUN.map((day) => (
                      <span key={day}>{day}</span>
                    ))}
                  </div>
                  <div className="grid grid-cols-7 gap-1">
                    {Array.from({ length: leadingBlanks }).map((_, index) => (
                      <div key={`blank-${index}`} className="min-h-[92px] rounded-lg bg-transparent" />
                    ))}
                    {daysInMonth.map((day) => {
                      const dateNum = Number(day.day.slice(-2));
                      const isToday = day.day === toIsoDate(today);
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
                            {day.contents.slice(0, 3).map((content) => {
                              const Icon = FORMAT_META[content.format].icon;
                              return (
                                <Link
                                  key={content.id}
                                  href={`/contents/${content.id}`}
                                  className="flex items-center gap-1 truncate rounded bg-surface-muted px-1.5 py-0.5 text-[11px] text-foreground/70 hover:bg-brand-50 hover:text-brand-700"
                                  title={content.title}
                                >
                                  <Icon className="h-3 w-3 shrink-0" />
                                  {content.title}
                                </Link>
                              );
                            })}
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
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-foreground">
                <Clock className="h-4 w-4 text-brand-600" /> Sem data definida
              </h3>
              {unscheduled.length === 0 ? (
                <p className="rounded-xl bg-surface-muted px-3 py-6 text-center text-xs text-foreground/45">
                  Tudo com data planejada.
                </p>
              ) : (
                <div className="space-y-2">
                  {unscheduled.map((content) => (
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
