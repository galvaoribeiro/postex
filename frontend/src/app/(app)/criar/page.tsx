"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Calendar,
  Check,
  ImagePlus,
  Plus,
  RefreshCw,
  Store,
  Tag,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { toast } from "sonner";

import { ContentPreview, StageChecklist } from "@/components/domain/content-preview";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { FieldHint, Input, Label, Textarea } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { Progress } from "@/components/ui/progress";
import { assetsApi, uploadLinkedImage } from "@/lib/api/assets";
import { productsApi, servicesApi } from "@/lib/api/catalog";
import { ApiError } from "@/lib/api/client";
import { contentsApi } from "@/lib/api/contents";
import type {
  AssetRead,
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
  const { data: catalogAssets, isSuccess: assetsReady } = useQuery({
    queryKey: queryKeys.assets({ status: "READY" }),
    queryFn: () => assetsApi.list({ status: "READY" }),
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
  const [creatingProduct, setCreatingProduct] = useState(false);
  const [newProductName, setNewProductName] = useState("");
  const [newProductPrice, setNewProductPrice] = useState("");
  const [newProductPhoto, setNewProductPhoto] = useState<File | null>(null);
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

  const catalogReady = products !== undefined && services !== undefined && assetsReady;
  const resolvedProductId =
    productId && products && !products.some((item) => item.id === productId) ? null : productId;
  const resolvedServiceId =
    serviceId && services && !services.some((item) => item.id === serviceId) ? null : serviceId;
  const selectedHasPhoto = itemHasReadyImage(
    catalogAssets,
    resolvedProductId,
    resolvedServiceId
  );

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
    Boolean(resolvedProductId || resolvedServiceId) &&
    selectedHasPhoto;

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
        queryClient.invalidateQueries({ queryKey: ["assets"] });
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
    setCreatingProduct(false);
    setProductId(id);
    setServiceId(null);
    setPhotoFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function selectService(id: string) {
    setCreatingProduct(false);
    setServiceId(id);
    setProductId(null);
    setPhotoFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function startCreateProduct() {
    setCreatingProduct(true);
    setProductId(null);
    setServiceId(null);
    setPhotoFile(null);
    setNewProductName("");
    setNewProductPrice("");
    setNewProductPhoto(null);
  }

  async function handleCreateProduct() {
    const name = newProductName.trim();
    if (name.length < 2) {
      toast.error("Informe o nome do produto.");
      return;
    }
    if (!newProductPhoto) {
      toast.error("Anexe a foto do produto. Ela entra na capa gerada.");
      return;
    }
    setBusy(true);
    try {
      const priceRaw = newProductPrice.trim().replace(",", ".");
      const created = await productsApi.create({
        name,
        price: priceRaw && !Number.isNaN(Number(priceRaw)) ? Number(priceRaw) : null,
        currency: "BRL",
        highlights: [],
        is_active: true,
      });
      await uploadLinkedImage(newProductPhoto, {
        kind: "PRODUCT_PHOTO",
        productId: created.id,
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.products });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      setProductId(created.id);
      setServiceId(null);
      setCreatingProduct(false);
      setNewProductName("");
      setNewProductPrice("");
      setNewProductPhoto(null);
      setPhotoFile(null);
      toast.success("Produto cadastrado. Ele entra neste post.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Nao foi possivel cadastrar o produto.");
    } finally {
      setBusy(false);
    }
  }

  async function handleContinueChoice() {
    if (!objective) {
      toast.error("Escolha um objetivo.");
      return;
    }
    if (creatingProduct) {
      toast.error("Cadastre o produto ou escolha um ja existente.");
      return;
    }
    if (!resolvedProductId && !resolvedServiceId) {
      toast.error("Escolha um produto ou cadastre um novo. Ele entra na geracao.");
      return;
    }
    if (!selectedHasPhoto) {
      if (!photoFile) {
        toast.error("Anexe a foto do produto. Ela entra na capa gerada.");
        return;
      }
      setBusy(true);
      try {
        await uploadLinkedImage(photoFile, {
          kind: "PRODUCT_PHOTO",
          productId: resolvedProductId,
          serviceId: resolvedServiceId,
        });
        queryClient.invalidateQueries({ queryKey: ["assets"] });
        setPhotoFile(null);
      } catch (err) {
        setBusy(false);
        toast.error(err instanceof Error ? err.message : "Falha ao enviar a foto.");
        return;
      }
      setBusy(false);
    }
    void begin(objective, resolvedProductId, resolvedServiceId);
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
    const nextAnswers = { ...answers, [currentQuestion.key]: draftAnswer.trim() };
    setAnswers(nextAnswers);
    const isLast = questionIndex >= questions.length - 1;
    if (isLast) {
      await finishQuestions(nextAnswers);
    } else {
      setQuestionIndex((index) => index + 1);
      setDraftAnswer("");
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
    Boolean(objective) &&
    !creatingProduct &&
    Boolean(resolvedProductId || resolvedServiceId) &&
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
        title="Criar"
        description="Escolha ou cadastre o produto, anexe a foto e defina o objetivo. Esse produto entra na geracao."
      />

      {bootingFromQuery && <PageSpinner label="Preparando..." />}

      {step === "choice" && !bootingFromQuery && (
        <ChoiceStep
          objective={objective}
          productId={resolvedProductId}
          serviceId={resolvedServiceId}
          products={products ?? []}
          services={services ?? []}
          assets={catalogAssets ?? []}
          creatingProduct={creatingProduct}
          newProductName={newProductName}
          newProductPrice={newProductPrice}
          newProductPhoto={newProductPhoto}
          photoFile={photoFile}
          fileInputRef={fileInputRef}
          selectedHasPhoto={selectedHasPhoto}
          loading={!catalogReady || busy}
          canContinue={canContinueChoice}
          onObjective={setObjective}
          onSelectProduct={selectProduct}
          onSelectService={selectService}
          onStartCreateProduct={startCreateProduct}
          onCancelCreateProduct={() => setCreatingProduct(false)}
          onNewProductName={setNewProductName}
          onNewProductPrice={setNewProductPrice}
          onNewProductPhoto={setNewProductPhoto}
          onPhoto={setPhotoFile}
          onCreateProduct={() => void handleCreateProduct()}
          onContinue={() => void handleContinueChoice()}
        />
      )}

      {step === "questions" && currentQuestion && (
        <QuestionStep
          question={currentQuestion}
          index={questionIndex}
          total={questions.length}
          draft={draftAnswer}
          busy={busy || isWatching}
          itemLabel={selectedProduct?.name ?? selectedService?.name ?? null}
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

function itemHasReadyImage(
  assets: AssetRead[] | undefined,
  productId: string | null,
  serviceId: string | null
): boolean {
  if (!assets || (!productId && !serviceId)) return false;
  return assets.some((asset) => {
    if (asset.status !== "READY" || !asset.mime_type.startsWith("image/")) return false;
    if (productId && asset.product_id === productId) return true;
    if (serviceId && asset.service_id === serviceId) return true;
    return false;
  });
}

function photoUrlFor(
  assets: AssetRead[],
  productId?: string | null,
  serviceId?: string | null
): string | null {
  const match = assets.find((asset) => {
    if (asset.status !== "READY" || !asset.url) return false;
    if (productId && asset.product_id === productId) return true;
    if (serviceId && asset.service_id === serviceId) return true;
    return false;
  });
  return match?.url ?? null;
}

function ChoiceStep({
  objective,
  productId,
  serviceId,
  products,
  services,
  assets,
  creatingProduct,
  newProductName,
  newProductPrice,
  newProductPhoto,
  photoFile,
  fileInputRef,
  selectedHasPhoto,
  loading,
  canContinue,
  onObjective,
  onSelectProduct,
  onSelectService,
  onStartCreateProduct,
  onCancelCreateProduct,
  onNewProductName,
  onNewProductPrice,
  onNewProductPhoto,
  onPhoto,
  onCreateProduct,
  onContinue,
}: {
  objective: ContentObjective | null;
  productId: string | null;
  serviceId: string | null;
  products: ProductRead[];
  services: ServiceRead[];
  assets: AssetRead[];
  creatingProduct: boolean;
  newProductName: string;
  newProductPrice: string;
  newProductPhoto: File | null;
  photoFile: File | null;
  fileInputRef: RefObject<HTMLInputElement | null>;
  selectedHasPhoto: boolean;
  loading: boolean;
  canContinue: boolean;
  onObjective: (value: ContentObjective) => void;
  onSelectProduct: (id: string) => void;
  onSelectService: (id: string) => void;
  onStartCreateProduct: () => void;
  onCancelCreateProduct: () => void;
  onNewProductName: (value: string) => void;
  onNewProductPrice: (value: string) => void;
  onNewProductPhoto: (file: File | null) => void;
  onPhoto: (file: File | null) => void;
  onCreateProduct: () => void;
  onContinue: () => void;
}) {
  const selectedPhotoUrl = photoUrlFor(assets, productId, serviceId);

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <section>
        <h2 className="text-sm font-semibold text-foreground">Qual produto vamos divulgar?</h2>
        <p className="mt-1 text-sm text-foreground/55">
          Cadastre um novo ou escolha um ja existente. Esse produto entra obrigatoriamente na
          geracao. A foto e anexada aqui, nao depois.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <CatalogChip
            active={creatingProduct}
            icon={<Plus className="h-3.5 w-3.5" />}
            onClick={onStartCreateProduct}
          >
            Novo produto
          </CatalogChip>
          {products.map((product) => (
            <CatalogChip
              key={product.id}
              active={!creatingProduct && productId === product.id}
              thumb={photoUrlFor(assets, product.id)}
              icon={<Tag className="h-3.5 w-3.5" />}
              onClick={() => onSelectProduct(product.id)}
            >
              {product.name}
              {product.price != null ? ` · ${formatCurrency(product.price, product.currency)}` : ""}
            </CatalogChip>
          ))}
        </div>
        {services.length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-medium uppercase tracking-wide text-foreground/45">
              Ou um servico ja cadastrado
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {services.map((service) => (
                <CatalogChip
                  key={service.id}
                  active={!creatingProduct && serviceId === service.id}
                  thumb={photoUrlFor(assets, null, service.id)}
                  icon={<Store className="h-3.5 w-3.5" />}
                  onClick={() => onSelectService(service.id)}
                >
                  {service.name}
                </CatalogChip>
              ))}
            </div>
          </div>
        )}

        {creatingProduct && (
          <div className="mt-4 space-y-3 rounded-2xl border border-brand-200 bg-brand-50/40 p-4">
            <p className="text-sm font-medium text-foreground">Cadastrar produto</p>
            <div>
              <Label htmlFor="new-product-name">Nome</Label>
              <Input
                id="new-product-name"
                value={newProductName}
                onChange={(event) => onNewProductName(event.target.value)}
                placeholder="Ex.: Vestido midi de linho"
              />
            </div>
            <div>
              <Label htmlFor="new-product-price">Preco (opcional)</Label>
              <Input
                id="new-product-price"
                inputMode="decimal"
                value={newProductPrice}
                onChange={(event) => onNewProductPrice(event.target.value)}
                placeholder="Ex.: 199,90"
              />
            </div>
            <PhotoField
              id="new-product-photo"
              label="Foto do produto"
              hint="Obrigatorio. Esta foto e a referencia da capa gerada."
              file={newProductPhoto}
              onChange={onNewProductPhoto}
            />
            <div className="flex gap-2">
              <Button variant="ghost" onClick={onCancelCreateProduct} disabled={loading}>
                Cancelar
              </Button>
              <Button onClick={onCreateProduct} loading={loading} className="flex-1">
                Cadastrar e usar neste post
              </Button>
            </div>
          </div>
        )}

        {!creatingProduct && (productId || serviceId) && !selectedHasPhoto && (
          <div className="mt-4 rounded-2xl border border-dashed border-brand-300 bg-brand-50/30 p-4">
            <PhotoField
              id="selected-product-photo"
              label="Foto deste produto"
              hint="Ainda nao tem foto. Anexe agora: ela entra na capa gerada."
              file={photoFile}
              inputRef={fileInputRef}
              previewUrl={selectedPhotoUrl}
              onChange={onPhoto}
            />
          </div>
        )}

        {!creatingProduct && selectedHasPhoto && selectedPhotoUrl && (
          <p className="mt-3 flex items-center gap-2 text-sm text-foreground/55">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={selectedPhotoUrl}
              alt=""
              className="h-10 w-10 rounded-lg object-cover"
            />
            Foto do produto pronta. Ela entra na capa.
          </p>
        )}
      </section>

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

      <Button size="lg" onClick={onContinue} disabled={!canContinue} loading={loading}>
        Continuar
      </Button>
    </div>
  );
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
