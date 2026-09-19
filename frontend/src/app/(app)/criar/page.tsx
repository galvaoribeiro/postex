"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Calendar,
  Check,
  RefreshCw,
  Sparkles,
  Store,
  Tag,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useRef, useState, type ReactNode, type RefObject } from "react";
import { toast } from "sonner";

import { ContentPreview, StageChecklist } from "@/components/domain/content-preview";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { FieldHint, Input, Label, Textarea } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { Progress } from "@/components/ui/progress";
import { assetsApi, readImageDimensions, uploadFileToSignedUrl } from "@/lib/api/assets";
import { productsApi, servicesApi } from "@/lib/api/catalog";
import { ApiError } from "@/lib/api/client";
import { contentsApi } from "@/lib/api/contents";
import type {
  ContentObjective,
  ContentRead,
  CreationQuestion,
  JobRead,
  ProductRead,
  ServiceRead,
} from "@/lib/api/types";
import { useJobWatcher } from "@/lib/hooks/use-job-watcher";
import { queryKeys } from "@/lib/query-keys";
import { cn, formatCurrency } from "@/lib/utils";

type Step = "choice" | "questions" | "generating" | "preview";

const OBJECTIVES: {
  value: ContentObjective;
  label: string;
  description: string;
}[] = [
  {
    value: "SELL",
    label: "Vender",
    description: "Mostrar um produto ou servico e convencer a pessoa a comprar.",
  },
  {
    value: "ATTRACT",
    label: "Atrair clientes",
    description: "Trazer gente nova para o perfil, sem pedir a compra agora.",
  },
  {
    value: "BRAND",
    label: "Fortalecer a marca",
    description: "Mostrar quem voce e e por que confiar no seu negocio.",
  },
];

function parseObjective(value: string | null): ContentObjective | null {
  if (value === "SELL" || value === "ATTRACT" || value === "BRAND") return value;
  return null;
}

export default function CriarPage() {
  return (
    <Suspense fallback={<PageSpinner label="Carregando..." />}>
      <CriarFlow />
    </Suspense>
  );
}

function CriarFlow() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { watch, isWatching } = useJobWatcher();

  const { data: products } = useQuery({
    queryKey: queryKeys.products,
    queryFn: () => productsApi.list(true),
  });
  const { data: services } = useQuery({
    queryKey: queryKeys.services,
    queryFn: () => servicesApi.list(true),
  });

  const [step, setStep] = useState<Step>("choice");
  const [objective, setObjective] = useState<ContentObjective | null>(() =>
    parseObjective(searchParams.get("objective"))
  );
  const [productId, setProductId] = useState<string | null>(() => searchParams.get("product"));
  const [serviceId, setServiceId] = useState<string | null>(() =>
    searchParams.get("product") ? null : searchParams.get("service")
  );
  const [questions, setQuestions] = useState<CreationQuestion[]>([]);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [draftAnswer, setDraftAnswer] = useState("");
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [stage, setStage] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [jobStatus, setJobStatus] = useState<JobRead["status"]>("PENDING");
  const [content, setContent] = useState<ContentRead | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [stayOnChoice, setStayOnChoice] = useState(false);

  const lastRequest = useRef<{
    objective: ContentObjective;
    productId: string | null;
    serviceId: string | null;
    answers: Record<string, string>;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const catalogReady = products !== undefined && services !== undefined;
  const resolvedProductId =
    productId && products && !products.some((item) => item.id === productId) ? null : productId;
  const resolvedServiceId =
    serviceId && services && !services.some((item) => item.id === serviceId) ? null : serviceId;

  const currentQuestion = questions[questionIndex] ?? null;
  const selectedProduct = products?.find((item) => item.id === resolvedProductId) ?? null;
  const selectedService = services?.find((item) => item.id === resolvedServiceId) ?? null;

  const urlObjective = parseObjective(searchParams.get("objective"));
  const matchesInboundQuery =
    Boolean(urlObjective) &&
    objective === urlObjective &&
    (searchParams.get("product") ? resolvedProductId === searchParams.get("product") : true) &&
    (searchParams.get("service") && !searchParams.get("product")
      ? resolvedServiceId === searchParams.get("service")
      : true);
  const bootReady =
    matchesInboundQuery &&
    !stayOnChoice &&
    catalogReady &&
    Boolean(objective) &&
    (objective !== "SELL" || Boolean(resolvedProductId || resolvedServiceId));

  const bootQuestions = useQuery({
    queryKey: queryKeys.creationQuestions({
      objective,
      product_id: resolvedProductId,
      service_id: resolvedServiceId,
    }),
    queryFn: () =>
      contentsApi.generateQuestions({
        objective: objective!,
        product_id: resolvedProductId || undefined,
        service_id: resolvedServiceId || undefined,
      }),
    enabled: bootReady && step === "choice",
  });

  const skipToQuestions =
    !stayOnChoice &&
    step === "choice" &&
    bootQuestions.isSuccess &&
    bootQuestions.data.length > 0;

  const generateContent = useCallback(
    async (payload: {
      objective: ContentObjective;
      productId: string | null;
      serviceId: string | null;
      answers: Record<string, string>;
    }) => {
      lastRequest.current = payload;
      setError(null);
      setStep("generating");
      setStage(null);
      setProgress(10);
      setJobStatus("PROCESSING");
      setContent(null);
      try {
        const accepted = await contentsApi.generate({
          objective: payload.objective,
          product_id: payload.productId || undefined,
          service_id: payload.serviceId || undefined,
          answers: payload.answers,
        });
        const job = await watch(accepted.job_id, accepted.kind, {
          showToast: false,
          intervalMs: 800,
          onStage: (nextStage) => setStage(nextStage),
          onUpdate: (current) => {
            setProgress(current.progress);
            setJobStatus(current.status);
            if (current.stage) setStage(current.stage);
          },
        });
        const contentId = job?.result?.content_id as string | undefined;
        if (!job || job.status !== "COMPLETED" || !contentId) {
          setError(job?.error_message ?? "Nao foi possivel gerar o conteudo.");
          return;
        }
        const created = await contentsApi.get(contentId);
        queryClient.invalidateQueries({ queryKey: ["contents"] });
        queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
        queryClient.invalidateQueries({ queryKey: queryKeys.products });
        queryClient.invalidateQueries({ queryKey: queryKeys.services });
        queryClient.invalidateQueries({ queryKey: queryKeys.business });
        setContent(created);
        setProgress(100);
        setJobStatus("COMPLETED");
        setStep("preview");
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Falha ao gerar o conteudo.");
      }
    },
    [queryClient, watch]
  );

  const begin = useCallback(
    async (
      nextObjective: ContentObjective,
      nextProductId: string | null,
      nextServiceId: string | null
    ) => {
      setBusy(true);
      setError(null);
      try {
        const list = await queryClient.fetchQuery({
          queryKey: queryKeys.creationQuestions({
            objective: nextObjective,
            product_id: nextProductId,
            service_id: nextServiceId,
          }),
          queryFn: () =>
            contentsApi.generateQuestions({
              objective: nextObjective,
              product_id: nextProductId || undefined,
              service_id: nextServiceId || undefined,
            }),
        });
        if (list.length === 0) {
          await generateContent({
            objective: nextObjective,
            productId: nextProductId,
            serviceId: nextServiceId,
            answers: {},
          });
          return;
        }
        setQuestions(list);
        setQuestionIndex(0);
        setAnswers({});
        setDraftAnswer("");
        setPhotoFile(null);
        setStep("questions");
      } catch (err) {
        toast.error(err instanceof ApiError ? err.message : "Nao foi possivel preparar as perguntas.");
      } finally {
        setBusy(false);
      }
    },
    [generateContent, queryClient]
  );

  function selectProduct(id: string) {
    setProductId(id);
    setServiceId(null);
  }

  function selectService(id: string) {
    setServiceId(id);
    setProductId(null);
  }

  function clearItem() {
    setProductId(null);
    setServiceId(null);
  }

  function handleContinueChoice() {
    if (!objective) {
      toast.error("Escolha um objetivo.");
      return;
    }
    if (objective === "SELL" && !productId && !serviceId) {
      toast.error("Para vender, escolha um produto ou servico.");
      return;
    }
    void begin(objective, resolvedProductId, resolvedServiceId);
  }

  async function uploadPhotoIfNeeded(): Promise<boolean> {
    if (!currentQuestion || currentQuestion.key !== "product_photo") return true;
    if (draftAnswer !== "upload_now") return true;
    if (!photoFile) {
      toast.error("Selecione a foto ou pule esta pergunta.");
      return false;
    }
    try {
      const ticket = await assetsApi.createUploadUrl({
        filename: photoFile.name,
        mime_type: photoFile.type || "image/jpeg",
        size_bytes: photoFile.size,
        kind: "PRODUCT_PHOTO",
        product_id: resolvedProductId,
        service_id: resolvedServiceId,
      });
      await uploadFileToSignedUrl(ticket, photoFile);
      const dimensions = await readImageDimensions(photoFile);
      await assetsApi.confirm(ticket.asset_id, {
        size_bytes: photoFile.size,
        width: dimensions?.width,
        height: dimensions?.height,
        analyze: false,
      });
      return true;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao enviar a foto.");
      return false;
    }
  }

  async function finishQuestions(nextAnswers: Record<string, string>) {
    if (!objective) return;
    await generateContent({
      objective,
      productId: resolvedProductId,
      serviceId: resolvedServiceId,
      answers: nextAnswers,
    });
  }

  async function handleQuestionNext() {
    if (!currentQuestion || !objective) return;
    if (currentQuestion.kind === "choice" && !draftAnswer) {
      toast.error("Escolha uma opcao ou pule.");
      return;
    }
    if (currentQuestion.kind === "text" && !draftAnswer.trim()) {
      toast.error("Escreva uma resposta ou pule.");
      return;
    }
    if (currentQuestion.kind === "money" && !draftAnswer.trim()) {
      toast.error("Informe o preco, escolha nao mostrar, ou pule.");
      return;
    }
    setBusy(true);
    const uploaded = await uploadPhotoIfNeeded();
    if (!uploaded) {
      setBusy(false);
      return;
    }
    const nextAnswers = { ...answers, [currentQuestion.key]: draftAnswer.trim() };
    setAnswers(nextAnswers);
    const isLast = questionIndex >= questions.length - 1;
    if (isLast) {
      await finishQuestions(nextAnswers);
    } else {
      setQuestionIndex((index) => index + 1);
      setDraftAnswer("");
      setPhotoFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
    setBusy(false);
  }

  async function handleQuestionSkip() {
    if (!currentQuestion || !objective) return;
    setBusy(true);
    try {
      const isLast = questionIndex >= questions.length - 1;
      if (isLast) {
        await finishQuestions(answers);
        return;
      }
      setQuestionIndex((index) => index + 1);
      setDraftAnswer("");
      setPhotoFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } finally {
      setBusy(false);
    }
  }

  const approveMutation = useMutation({
    mutationFn: (id: string) => contentsApi.approve(id),
    onSuccess: (updated) => {
      setContent(updated);
      queryClient.invalidateQueries({ queryKey: ["contents"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
      toast.success("Conteudo aprovado.");
    },
    onError: (err: unknown) =>
      toast.error(err instanceof ApiError ? err.message : "Nao foi possivel aprovar."),
  });

  function handleRedo() {
    const payload = lastRequest.current;
    if (!payload) return;
    void generateContent(payload);
  }

  const canContinueChoice =
    Boolean(objective) && (objective !== "SELL" || Boolean(resolvedProductId || resolvedServiceId));
  const bootingFromQuery =
    bootReady && step === "choice" && (bootQuestions.isPending || skipToQuestions);

  if (skipToQuestions) {
    setQuestions(bootQuestions.data);
    setQuestionIndex(0);
    setAnswers({});
    setDraftAnswer("");
    setPhotoFile(null);
    setStep("questions");
  }

  return (
    <div>
      <PageHeader
        title="Criar"
        description="Produto, objetivo e ate tres perguntas. Um job, um preview."
      />

      {bootingFromQuery && <PageSpinner label="Preparando..." />}

      {step === "choice" && !bootingFromQuery && (
        <ChoiceStep
          objective={objective}
          productId={resolvedProductId}
          serviceId={resolvedServiceId}
          products={products ?? []}
          services={services ?? []}
          loading={!catalogReady || busy}
          canContinue={canContinueChoice}
          onObjective={setObjective}
          onSelectProduct={selectProduct}
          onSelectService={selectService}
          onClearItem={clearItem}
          onContinue={handleContinueChoice}
        />
      )}

      {step === "questions" && currentQuestion && (
        <QuestionStep
          question={currentQuestion}
          index={questionIndex}
          total={questions.length}
          draft={draftAnswer}
          photoFile={photoFile}
          fileInputRef={fileInputRef}
          busy={busy || isWatching}
          itemLabel={selectedProduct?.name ?? selectedService?.name ?? null}
          onDraft={setDraftAnswer}
          onPhoto={setPhotoFile}
          onSkip={() => void handleQuestionSkip()}
          onNext={() => void handleQuestionNext()}
          onBack={() => {
            if (questionIndex === 0) {
              setStayOnChoice(true);
              setStep("choice");
              return;
            }
            setQuestionIndex((index) => index - 1);
            setDraftAnswer("");
            setPhotoFile(null);
          }}
        />
      )}

      {step === "generating" && (
        <GeneratingStep
          stage={stage}
          progress={progress}
          status={jobStatus}
          error={error}
          onRetry={handleRedo}
          onBack={() => setStep("choice")}
        />
      )}

      {step === "preview" && content && (
        <div className="space-y-6">
          <ContentPreview
            content={content}
            actions={
              <>
                <Button
                  icon={<Check className="h-4 w-4" />}
                  onClick={() => approveMutation.mutate(content.id)}
                  loading={approveMutation.isPending}
                  disabled={content.status === "APPROVED" || content.status === "SCHEDULED"}
                >
                  {content.status === "APPROVED" || content.status === "SCHEDULED"
                    ? "Aprovado"
                    : "Aprovar"}
                </Button>
                <Button
                  variant="outline"
                  icon={<RefreshCw className="h-4 w-4" />}
                  onClick={handleRedo}
                  loading={isWatching}
                >
                  Refazer
                </Button>
                <Button
                  variant="outline"
                  icon={<Calendar className="h-4 w-4" />}
                  onClick={() => setScheduleOpen(true)}
                >
                  Agendar
                </Button>
              </>
            }
          />
          <div className="flex justify-center">
            <button
              type="button"
              onClick={() => router.push(`/contents/${content.id}`)}
              className="text-sm font-medium text-brand-700 hover:underline"
            >
              Abrir no editor completo
            </button>
          </div>
          <ScheduleDialog
            open={scheduleOpen}
            content={content}
            onClose={() => setScheduleOpen(false)}
            onScheduled={(updated) => {
              setContent(updated);
              setScheduleOpen(false);
            }}
          />
        </div>
      )}
    </div>
  );
}

function ChoiceStep({
  objective,
  productId,
  serviceId,
  products,
  services,
  loading,
  canContinue,
  onObjective,
  onSelectProduct,
  onSelectService,
  onClearItem,
  onContinue,
}: {
  objective: ContentObjective | null;
  productId: string | null;
  serviceId: string | null;
  products: ProductRead[];
  services: ServiceRead[];
  loading: boolean;
  canContinue: boolean;
  onObjective: (value: ContentObjective) => void;
  onSelectProduct: (id: string) => void;
  onSelectService: (id: string) => void;
  onClearItem: () => void;
  onContinue: () => void;
}) {
  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <section>
        <h2 className="text-sm font-semibold text-foreground">Qual o objetivo?</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          {OBJECTIVES.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => onObjective(item.value)}
              className={cn(
                "rounded-2xl border px-4 py-4 text-left transition-colors",
                objective === item.value
                  ? "border-brand-500 bg-brand-50"
                  : "border-border-subtle bg-surface hover:border-brand-200"
              )}
            >
              <p className="font-semibold text-foreground">{item.label}</p>
              <p className="mt-1 text-xs leading-relaxed text-foreground/55">{item.description}</p>
            </button>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-foreground">O que vamos divulgar?</h2>
        <p className="mt-1 text-sm text-foreground/55">
          {objective === "SELL"
            ? "Obrigatorio para vender. Escolha um produto ou servico."
            : "Opcional. Sem item, o Motor fala da marca como um todo."}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {objective !== "SELL" && (
            <CatalogChip
              active={!productId && !serviceId}
              icon={<Sparkles className="h-3.5 w-3.5" />}
              onClick={onClearItem}
            >
              So a marca
            </CatalogChip>
          )}
          {products.map((product) => (
            <CatalogChip
              key={product.id}
              active={productId === product.id}
              icon={<Tag className="h-3.5 w-3.5" />}
              onClick={() => onSelectProduct(product.id)}
            >
              {product.name}
              {product.price != null ? ` · ${formatCurrency(product.price, product.currency)}` : ""}
            </CatalogChip>
          ))}
          {services.map((service) => (
            <CatalogChip
              key={service.id}
              active={serviceId === service.id}
              icon={<Store className="h-3.5 w-3.5" />}
              onClick={() => onSelectService(service.id)}
            >
              {service.name}
            </CatalogChip>
          ))}
        </div>
        {products.length === 0 && services.length === 0 && (
          <p className="mt-3 text-sm text-foreground/45">
            Cadastre um produto ou servico em Configuracoes se quiser vender algo especifico.
          </p>
        )}
      </section>

      <p className="text-xs text-foreground/45">Estilo: Automatico. Sem escolher pilares editorial.</p>

      <Button size="lg" onClick={onContinue} disabled={!canContinue} loading={loading}>
        Continuar
      </Button>
    </div>
  );
}

function CatalogChip({
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

function QuestionStep({
  question,
  index,
  total,
  draft,
  photoFile,
  fileInputRef,
  busy,
  itemLabel,
  onDraft,
  onPhoto,
  onSkip,
  onNext,
  onBack,
}: {
  question: CreationQuestion;
  index: number;
  total: number;
  draft: string;
  photoFile: File | null;
  fileInputRef: RefObject<HTMLInputElement | null>;
  busy: boolean;
  itemLabel: string | null;
  onDraft: (value: string) => void;
  onPhoto: (file: File | null) => void;
  onSkip: () => void;
  onNext: () => void;
  onBack: () => void;
}) {
  return (
    <div className="mx-auto max-w-lg">
      <button
        type="button"
        onClick={onBack}
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-foreground/55 hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Voltar
      </button>
      <p className="text-xs font-medium uppercase tracking-wide text-foreground/45">
        Pergunta {index + 1} de {total}
        {itemLabel ? ` · ${itemLabel}` : ""}
      </p>
      <h2 className="mt-2 text-2xl font-semibold text-foreground">{question.question}</h2>

      <div className="mt-6 space-y-4">
        {question.kind === "choice" && (
          <div className="grid gap-2">
            {question.options.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => onDraft(option.value)}
                className={cn(
                  "rounded-xl border px-4 py-3 text-left text-sm font-medium transition-colors",
                  draft === option.value
                    ? "border-brand-500 bg-brand-50 text-brand-800"
                    : "border-border-subtle hover:border-brand-200"
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        )}

        {question.key === "product_photo" && draft === "upload_now" && (
          <div>
            <Label htmlFor="creation-photo">Arquivo</Label>
            <input
              id="creation-photo"
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={(event) => onPhoto(event.target.files?.[0] ?? null)}
              className="block w-full text-sm text-foreground/70"
            />
            <FieldHint>
              {photoFile ? photoFile.name : "JPG, PNG ou WebP. A foto fica vinculada ao item."}
            </FieldHint>
          </div>
        )}

        {question.kind === "text" && (
          <Textarea
            rows={3}
            value={draft}
            onChange={(event) => onDraft(event.target.value)}
            placeholder="Uma frase, no seu tom."
          />
        )}

        {question.kind === "money" && (
          <div className="space-y-3">
            <Input
              inputMode="decimal"
              value={draft === "hide" ? "" : draft}
              onChange={(event) => onDraft(event.target.value)}
              placeholder="Ex.: 199,90"
            />
            {question.options.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => onDraft(option.value)}
                className={cn(
                  "rounded-xl border px-4 py-3 text-left text-sm font-medium",
                  draft === option.value
                    ? "border-brand-500 bg-brand-50 text-brand-800"
                    : "border-border-subtle hover:border-brand-200"
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="mt-8 flex gap-2">
        <Button variant="ghost" onClick={onSkip} disabled={busy}>
          Pular
        </Button>
        <Button onClick={onNext} loading={busy} className="flex-1">
          {index === total - 1 ? "Gerar conteudo" : "Proxima"}
        </Button>
      </div>
    </div>
  );
}

function GeneratingStep({
  stage,
  progress,
  status,
  error,
  onRetry,
  onBack,
}: {
  stage: string | null;
  progress: number;
  status: JobRead["status"];
  error: string | null;
  onRetry: () => void;
  onBack: () => void;
}) {
  return (
    <Card className="mx-auto max-w-md">
      <CardContent className="space-y-5 p-6 pt-6">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Gerando seu conteudo</h2>
          <p className="mt-1 text-sm text-foreground/55">
            Um job so, com as etapas visiveis. Nada de video falso no meio do caminho.
          </p>
        </div>
        <Progress value={progress} />
        <StageChecklist stage={stage} status={status} />
        {error && (
          <div className="space-y-3 rounded-xl bg-danger-bg px-4 py-3 text-sm text-danger-fg">
            <p>{error}</p>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={onBack}>
                Voltar
              </Button>
              <Button size="sm" onClick={onRetry}>
                Tentar de novo
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ScheduleDialog({
  open,
  content,
  onClose,
  onScheduled,
}: {
  open: boolean;
  content: ContentRead;
  onClose: () => void;
  onScheduled: (updated: ContentRead) => void;
}) {
  const queryClient = useQueryClient();
  const [date, setDate] = useState(content.planned_date ?? "");

  const mutation = useMutation({
    mutationFn: () => contentsApi.schedule(content.id, date),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["contents"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
      queryClient.invalidateQueries({ queryKey: ["calendar"] });
      toast.success("Data planejada.");
      onScheduled(updated);
    },
    onError: (err: unknown) =>
      toast.error(err instanceof ApiError ? err.message : "Nao foi possivel agendar."),
  });

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Agendar"
      description="Define o dia no calendario. A publicacao automatica no Instagram ainda nao existe."
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancelar
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!date}
            loading={mutation.isPending}
          >
            Confirmar data
          </Button>
        </>
      }
    >
      <Label htmlFor="planned_date">Dia</Label>
      <Input
        id="planned_date"
        type="date"
        value={date}
        onChange={(event) => setDate(event.target.value)}
      />
    </Dialog>
  );
}
