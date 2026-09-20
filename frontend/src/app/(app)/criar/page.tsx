"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, Download, ImagePlus, Plus, RefreshCw, Tag } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import { toast } from "sonner";

import { CampaignPreview, StageChecklist } from "@/components/domain/campaign-preview";
import { DESTINATION_META } from "@/components/domain/destination-badge";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FieldHint, Input, Label, Textarea } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { Progress } from "@/components/ui/progress";
import { assetsApi, uploadLinkedImage } from "@/lib/api/assets";
import { campaignsApi } from "@/lib/api/campaigns";
import { productsApi } from "@/lib/api/catalog";
import { ApiError } from "@/lib/api/client";
import type {
  AssetRead,
  CampaignDestination,
  CampaignOutput,
  CampaignRead,
  CreationQuestion,
  JobRead,
  ProductRead,
} from "@/lib/api/types";
import { useJobWatcher } from "@/lib/hooks/use-job-watcher";
import { queryKeys } from "@/lib/query-keys";
import { cn, formatCurrency } from "@/lib/utils";

type Step = "choice" | "questions" | "generating" | "preview";

const DESTINATIONS: {
  value: CampaignDestination;
  label: string;
  description: string;
  defaults: CampaignOutput[];
}[] = [
  {
    value: "INSTAGRAM",
    label: "Instagram",
    description: "Imagem comercial e copy prontas para o feed.",
    defaults: ["IMAGE", "COPY"],
  },
  {
    value: "TIKTOK",
    label: "TikTok",
    description: "Video vertical, roteiro e legenda nativos.",
    defaults: ["VIDEO", "COPY"],
  },
  {
    value: "TIKTOK_SHOP",
    label: "TikTok Shop",
    description: "Video comercial com produto visivel e CTA de compra.",
    defaults: ["VIDEO", "COPY"],
  },
];

function parseDestination(value: string | null): CampaignDestination | null {
  if (value === "INSTAGRAM" || value === "TIKTOK" || value === "TIKTOK_SHOP") return value;
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
  const { data: catalogAssets, isSuccess: assetsReady } = useQuery({
    queryKey: queryKeys.assets({ status: "READY" }),
    queryFn: () => assetsApi.list({ status: "READY" }),
  });

  const [step, setStep] = useState<Step>("choice");
  const [destination, setDestination] = useState<CampaignDestination | null>(() =>
    parseDestination(searchParams.get("destination"))
  );
  const [outputs, setOutputs] = useState<CampaignOutput[]>(["IMAGE", "COPY"]);
  const [productId, setProductId] = useState<string | null>(() => searchParams.get("product"));
  const [questions, setQuestions] = useState<CreationQuestion[]>([]);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [draftAnswer, setDraftAnswer] = useState("");
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [creatingProduct, setCreatingProduct] = useState(false);
  const [newProductName, setNewProductName] = useState("");
  const [newProductPrice, setNewProductPrice] = useState("");
  const [newProductPhoto, setNewProductPhoto] = useState<File | null>(null);
  const [stage, setStage] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [jobStatus, setJobStatus] = useState<JobRead["status"]>("PENDING");
  const [campaign, setCampaign] = useState<CampaignRead | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stayOnChoice, setStayOnChoice] = useState(false);
  const [regenerating, setRegenerating] = useState<CampaignOutput | null>(null);

  const lastRequest = useRef<{
    destination: CampaignDestination;
    productId: string;
    outputs: CampaignOutput[];
    answers: Record<string, string>;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const catalogReady = products !== undefined && assetsReady;
  const resolvedProductId =
    productId && products && !products.some((item) => item.id === productId) ? null : productId;
  const selectedHasPhoto = itemHasReadyImage(catalogAssets, resolvedProductId);
  const currentQuestion = questions[questionIndex] ?? null;
  const selectedProduct = products?.find((item) => item.id === resolvedProductId) ?? null;

  const urlDestination = parseDestination(searchParams.get("destination"));
  const matchesInboundQuery =
    Boolean(urlDestination) &&
    destination === urlDestination &&
    (searchParams.get("product") ? resolvedProductId === searchParams.get("product") : true);
  const bootReady =
    matchesInboundQuery &&
    !stayOnChoice &&
    catalogReady &&
    Boolean(destination) &&
    Boolean(resolvedProductId) &&
    selectedHasPhoto;

  const bootQuestions = useQuery({
    queryKey: queryKeys.campaignQuestions({
      destination,
      product_id: resolvedProductId,
    }),
    queryFn: () =>
      campaignsApi.generateQuestions({
        product_id: resolvedProductId!,
        destination: destination!,
      }),
    enabled: bootReady && step === "choice",
  });

  const skipToQuestions =
    !stayOnChoice && step === "choice" && bootQuestions.isSuccess && bootQuestions.data.length > 0;

  const generateCampaign = useCallback(
    async (payload: {
      destination: CampaignDestination;
      productId: string;
      outputs: CampaignOutput[];
      answers: Record<string, string>;
    }) => {
      lastRequest.current = payload;
      setError(null);
      setStep("generating");
      setStage(null);
      setProgress(10);
      setJobStatus("PROCESSING");
      setCampaign(null);
      try {
        const accepted = await campaignsApi.generate({
          product_id: payload.productId,
          destination: payload.destination,
          outputs: payload.outputs,
          answers: payload.answers,
        });
        const job = await watch(accepted.job_id, accepted.kind, {
          showToast: false,
          timeoutMs: 180_000,
          onStage: (next, current) => {
            setStage(next);
            setProgress(current.progress);
            setJobStatus(current.status);
          },
          onUpdate: (current) => {
            setProgress(current.progress);
            setJobStatus(current.status);
          },
        });
        if (!job || job.status !== "COMPLETED") {
          setError(job?.error_message ?? "Nao foi possivel gerar a campanha.");
          return;
        }
        const created = await campaignsApi.get(accepted.campaign_id);
        setCampaign(created);
        setStep("preview");
        queryClient.invalidateQueries({ queryKey: queryKeys.campaigns() });
        queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Nao foi possivel gerar a campanha.");
      }
    },
    [queryClient, watch]
  );

  async function ensurePhoto(targetProductId: string) {
    if (itemHasReadyImage(catalogAssets, targetProductId) || !photoFile) return;
    await uploadLinkedImage(photoFile, { productId: targetProductId, kind: "PRODUCT_PHOTO" });
    await queryClient.invalidateQueries({ queryKey: queryKeys.assets() });
  }

  async function finishQuestions(nextAnswers: Record<string, string>) {
    if (!destination || !resolvedProductId) return;
    await ensurePhoto(resolvedProductId);
    await generateCampaign({
      destination,
      productId: resolvedProductId,
      outputs,
      answers: nextAnswers,
    });
  }

  async function handleContinueChoice() {
    if (!destination || !resolvedProductId) {
      toast.error("Escolha o produto e o destino.");
      return;
    }
    if (!selectedHasPhoto && !photoFile) {
      toast.error("Anexe uma foto do produto.");
      return;
    }
    setBusy(true);
    try {
      await ensurePhoto(resolvedProductId);
      const nextQuestions = await campaignsApi.generateQuestions({
        product_id: resolvedProductId,
        destination,
      });
      if (nextQuestions.length === 0) {
        await finishQuestions({});
        return;
      }
      setQuestions(nextQuestions);
      setQuestionIndex(0);
      setAnswers({});
      setDraftAnswer("");
      setStep("questions");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Nao foi possivel continuar.");
    } finally {
      setBusy(false);
    }
  }

  function selectProduct(id: string) {
    setCreatingProduct(false);
    setProductId(id);
    setPhotoFile(null);
  }

  async function handleCreateProduct() {
    if (!newProductName.trim()) {
      toast.error("Informe o nome do produto.");
      return;
    }
    if (!newProductPhoto) {
      toast.error("Anexe a foto do produto.");
      return;
    }
    setBusy(true);
    try {
      const price = newProductPrice.trim() ? Number(newProductPrice.replace(",", ".")) : undefined;
      const product = await productsApi.create({
        name: newProductName.trim(),
        price: price != null && !Number.isNaN(price) ? price : undefined,
      });
      await uploadLinkedImage(newProductPhoto, { productId: product.id, kind: "PRODUCT_PHOTO" });
      await queryClient.invalidateQueries({ queryKey: queryKeys.products });
      await queryClient.invalidateQueries({ queryKey: queryKeys.assets() });
      setProductId(product.id);
      setCreatingProduct(false);
      setNewProductName("");
      setNewProductPrice("");
      setNewProductPhoto(null);
      toast.success("Produto cadastrado.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Nao foi possivel cadastrar o produto.");
    } finally {
      setBusy(false);
    }
  }

  async function handleQuestionNext() {
    if (!currentQuestion) return;
    if (currentQuestion.kind === "choice" && !draftAnswer) {
      toast.error("Escolha uma opcao ou pule.");
      return;
    }
    if ((currentQuestion.kind === "text" || currentQuestion.kind === "money") && !draftAnswer.trim()) {
      toast.error("Responda ou pule.");
      return;
    }
    setBusy(true);
    const nextAnswers = { ...answers, [currentQuestion.key]: draftAnswer.trim() };
    setAnswers(nextAnswers);
    if (questionIndex >= questions.length - 1) {
      await finishQuestions(nextAnswers);
    } else {
      setQuestionIndex((index) => index + 1);
      setDraftAnswer("");
    }
    setBusy(false);
  }

  async function handleQuestionSkip() {
    if (!currentQuestion) return;
    setBusy(true);
    try {
      if (questionIndex >= questions.length - 1) {
        await finishQuestions(answers);
        return;
      }
      setQuestionIndex((index) => index + 1);
      setDraftAnswer("");
    } finally {
      setBusy(false);
    }
  }

  const approveMutation = useMutation({
    mutationFn: (id: string) => campaignsApi.approve(id),
    onSuccess: (updated) => {
      setCampaign(updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.campaigns() });
      toast.success("Campanha aprovada.");
    },
    onError: (err: unknown) =>
      toast.error(err instanceof ApiError ? err.message : "Nao foi possivel aprovar."),
  });

  async function handleRegenerate(output: CampaignOutput) {
    if (!campaign) return;
    setRegenerating(output);
    try {
      const accepted = await campaignsApi.regenerate(campaign.id, { output });
      const job = await watch(accepted.job_id, accepted.kind, { showToast: true });
      if (job?.status === "COMPLETED") {
        setCampaign(await campaignsApi.get(campaign.id));
      }
    } finally {
      setRegenerating(null);
    }
  }

  function applyDestination(next: CampaignDestination) {
    setDestination(next);
    const preset = DESTINATIONS.find((item) => item.value === next);
    if (preset) setOutputs(preset.defaults);
  }

  function toggleOutput(output: CampaignOutput) {
    setOutputs((current) => {
      if (current.includes(output)) {
        if (output === "COPY") return current;
        return current.filter((item) => item !== output);
      }
      return [...current, output];
    });
  }

  const canContinueChoice =
    Boolean(destination) &&
    !creatingProduct &&
    Boolean(resolvedProductId) &&
    (selectedHasPhoto || Boolean(photoFile));
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
        title="Gerar campanha"
        description="Entregue o produto. A plataforma decide o conteudo que vende."
      />

      {bootingFromQuery && <PageSpinner label="Preparando..." />}

      {step === "choice" && !bootingFromQuery && (
        <div className="mx-auto max-w-2xl space-y-8">
          <section>
            <h2 className="text-sm font-semibold text-foreground">Qual produto vamos vender?</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              <CatalogChip
                active={creatingProduct}
                icon={<Plus className="h-3.5 w-3.5" />}
                onClick={() => setCreatingProduct(true)}
              >
                Novo produto
              </CatalogChip>
              {(products ?? []).map((product) => (
                <CatalogChip
                  key={product.id}
                  active={!creatingProduct && resolvedProductId === product.id}
                  thumb={photoUrlFor(catalogAssets ?? [], product.id)}
                  icon={<Tag className="h-3.5 w-3.5" />}
                  onClick={() => selectProduct(product.id)}
                >
                  {product.name}
                  {product.price != null ? ` · ${formatCurrency(product.price, product.currency)}` : ""}
                </CatalogChip>
              ))}
            </div>
            {creatingProduct && (
              <div className="mt-4 space-y-3 rounded-2xl border border-brand-200 bg-brand-50/40 p-4">
                <Label htmlFor="new-product-name">Nome</Label>
                <Input
                  id="new-product-name"
                  value={newProductName}
                  onChange={(event) => setNewProductName(event.target.value)}
                  placeholder="Ex.: Bolsa de couro caramelo"
                />
                <Label htmlFor="new-product-price">Preco (opcional)</Label>
                <Input
                  id="new-product-price"
                  inputMode="decimal"
                  value={newProductPrice}
                  onChange={(event) => setNewProductPrice(event.target.value)}
                  placeholder="Ex.: 199,90"
                />
                <PhotoField
                  id="new-product-photo"
                  label="Foto do produto"
                  hint="Obrigatorio. A foto condiciona imagem e video."
                  file={newProductPhoto}
                  onChange={setNewProductPhoto}
                />
                <div className="flex gap-2">
                  <Button variant="ghost" onClick={() => setCreatingProduct(false)} disabled={busy}>
                    Cancelar
                  </Button>
                  <Button onClick={() => void handleCreateProduct()} loading={busy} className="flex-1">
                    Cadastrar produto
                  </Button>
                </div>
              </div>
            )}
            {!creatingProduct && resolvedProductId && !selectedHasPhoto && (
              <div className="mt-4 rounded-2xl border border-dashed border-brand-300 bg-brand-50/30 p-4">
                <PhotoField
                  id="selected-product-photo"
                  label="Foto deste produto"
                  hint="Anexe agora: ela entra na geracao."
                  file={photoFile}
                  inputRef={fileInputRef}
                  onChange={setPhotoFile}
                />
              </div>
            )}
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground">Onde publicar?</h2>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              {DESTINATIONS.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  onClick={() => applyDestination(item.value)}
                  className={cn(
                    "rounded-2xl border px-4 py-4 text-left transition-colors",
                    destination === item.value
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

          {destination && (
            <section>
              <h2 className="text-sm font-semibold text-foreground">O que gerar?</h2>
              <p className="mt-1 text-sm text-foreground/55">
                Combinacao recomendada para {DESTINATION_META[destination].label}. Ajuste se quiser.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {(["IMAGE", "VIDEO", "COPY"] as CampaignOutput[]).map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => toggleOutput(item)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-sm",
                      outputs.includes(item)
                        ? "border-brand-500 bg-brand-50 text-brand-800"
                        : "border-border-subtle text-foreground/60"
                    )}
                  >
                    {item === "IMAGE" ? "Imagem" : item === "VIDEO" ? "Video" : "Copy"}
                  </button>
                ))}
              </div>
            </section>
          )}

          <Button
            size="lg"
            onClick={() => void handleContinueChoice()}
            disabled={!canContinueChoice}
            loading={busy}
          >
            Gerar campanha
          </Button>
        </div>
      )}

      {step === "questions" && currentQuestion && (
        <QuestionStep
          question={currentQuestion}
          index={questionIndex}
          total={questions.length}
          draft={draftAnswer}
          busy={busy || isWatching}
          itemLabel={selectedProduct?.name ?? null}
          onDraft={setDraftAnswer}
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
          }}
        />
      )}

      {step === "generating" && (
        <Card className="mx-auto max-w-md">
          <CardContent className="space-y-5 p-6 pt-6">
            <div>
              <h2 className="text-lg font-semibold text-foreground">Gerando sua campanha</h2>
              <p className="mt-1 text-sm text-foreground/55">
                Copy, imagem e video sobem em etapas. Voce pode exportar ao terminar.
              </p>
            </div>
            <Progress value={progress} />
            <StageChecklist stage={stage} status={jobStatus} outputs={outputs} />
            {error && (
              <div className="space-y-3 rounded-xl bg-danger-bg px-4 py-3 text-sm text-danger-fg">
                <p>{error}</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setStep("choice")}>
                    Voltar
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => lastRequest.current && void generateCampaign(lastRequest.current)}
                  >
                    Tentar de novo
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {step === "preview" && campaign && (
        <div className="space-y-6">
          <CampaignPreview
            campaign={campaign}
            onRegenerate={(output) => void handleRegenerate(output)}
            regenerating={regenerating}
            actions={
              <>
                <Button
                  icon={<Check className="h-4 w-4" />}
                  onClick={() => approveMutation.mutate(campaign.id)}
                  loading={approveMutation.isPending}
                  disabled={campaign.status === "APPROVED"}
                >
                  {campaign.status === "APPROVED" ? "Aprovada" : "Aprovar"}
                </Button>
                <Button
                  variant="outline"
                  icon={<RefreshCw className="h-4 w-4" />}
                  onClick={() => lastRequest.current && void generateCampaign(lastRequest.current)}
                  loading={isWatching}
                >
                  Refazer
                </Button>
                <Button
                  variant="outline"
                  icon={<Download className="h-4 w-4" />}
                  onClick={() => router.push(`/contents/${campaign.id}`)}
                >
                  Abrir campanha
                </Button>
              </>
            }
          />
        </div>
      )}
    </div>
  );
}

function itemHasReadyImage(assets: AssetRead[] | undefined, productId: string | null): boolean {
  if (!assets || !productId) return false;
  return assets.some(
    (asset) =>
      asset.status === "READY" &&
      asset.mime_type.startsWith("image/") &&
      asset.product_id === productId
  );
}

function photoUrlFor(assets: AssetRead[], productId?: string | null): string | null {
  const match = assets.find(
    (asset) => asset.status === "READY" && asset.url && productId && asset.product_id === productId
  );
  return match?.url ?? null;
}

function PhotoField({
  id,
  label,
  hint,
  file,
  previewUrl,
  inputRef,
  onChange,
}: {
  id: string;
  label: string;
  hint: string;
  file: File | null;
  previewUrl?: string | null;
  inputRef?: RefObject<HTMLInputElement | null>;
  onChange: (file: File | null) => void;
}) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!file) {
      setObjectUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setObjectUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const localPreview = objectUrl ?? previewUrl ?? null;
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <label
        htmlFor={id}
        className="mt-1 flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-brand-300 bg-surface px-3 py-3 text-sm hover:border-brand-400"
      >
        {localPreview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={localPreview} alt="" className="h-14 w-14 rounded-lg object-cover" />
        ) : (
          <span className="flex h-14 w-14 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
            <ImagePlus className="h-5 w-5" />
          </span>
        )}
        <span className="text-foreground/70">
          {file ? file.name : "Escolher foto (JPG, PNG ou WebP)"}
        </span>
      </label>
      <input
        id={id}
        ref={inputRef}
        type="file"
        accept="image/*"
        className="sr-only"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />
      <FieldHint>{hint}</FieldHint>
    </div>
  );
}

function CatalogChip({
  active,
  icon,
  thumb,
  onClick,
  children,
}: {
  active: boolean;
  icon: ReactNode;
  thumb?: string | null;
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
      {thumb ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={thumb} alt="" className="h-5 w-5 rounded-full object-cover" />
      ) : (
        icon
      )}
      {children}
    </button>
  );
}

function QuestionStep({
  question,
  index,
  total,
  draft,
  busy,
  itemLabel,
  onDraft,
  onSkip,
  onNext,
  onBack,
}: {
  question: CreationQuestion;
  index: number;
  total: number;
  draft: string;
  busy: boolean;
  itemLabel: string | null;
  onDraft: (value: string) => void;
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
        {question.kind === "text" && (
          <Textarea rows={3} value={draft} onChange={(event) => onDraft(event.target.value)} />
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
          {index === total - 1 ? "Gerar campanha" : "Proxima"}
        </Button>
      </div>
    </div>
  );
}
