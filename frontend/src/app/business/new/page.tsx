"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Building2, Package, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { FieldHint, FieldError, Input, Label, Textarea } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { assetsApi, readImageDimensions, uploadFileToSignedUrl } from "@/lib/api/assets";
import { businessApi } from "@/lib/api/business";
import { productsApi } from "@/lib/api/catalog";
import { ApiError } from "@/lib/api/client";
import type { CampaignDestination } from "@/lib/api/types";
import { useSession } from "@/lib/hooks/use-session";
import { queryKeys } from "@/lib/query-keys";
import { cn } from "@/lib/utils";

const DESTINATIONS: { value: CampaignDestination; label: string; description: string }[] = [
  { value: "INSTAGRAM", label: "Instagram", description: "Imagem comercial e copy para o feed." },
  { value: "TIKTOK", label: "TikTok", description: "Video vertical, roteiro e legenda." },
  { value: "TIKTOK_SHOP", label: "TikTok Shop", description: "Video comercial com CTA de compra." },
];

export default function BusinessOnboardingPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: session, isLoading: sessionLoading } = useSession();

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [segment, setSegment] = useState("");
  const [description, setDescription] = useState("");
  const [itemName, setItemName] = useState("");
  const [itemPrice, setItemPrice] = useState("");
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [destination, setDestination] = useState<CampaignDestination | null>(null);
  const [nameError, setNameError] = useState<string | undefined>();
  const [segmentError, setSegmentError] = useState<string | undefined>();

  const createBusiness = useMutation({ mutationFn: businessApi.create });

  useEffect(() => {
    if (!sessionLoading && session?.has_business && !busy) {
      router.replace("/inicio");
    }
  }, [busy, router, session, sessionLoading]);

  if (sessionLoading || !session) {
    return <PageSpinner label="Carregando..." />;
  }

  if (session.has_business && !busy) {
    return <PageSpinner label="Redirecionando..." />;
  }

  function goFromStep1() {
    const nextName = name.trim();
    const nextSegment = segment.trim();
    setNameError(nextName.length < 2 ? "Informe o nome do negocio." : undefined);
    setSegmentError(nextSegment.length < 2 ? "Informe o segmento." : undefined);
    if (nextName.length < 2 || nextSegment.length < 2) return;
    setStep(2);
  }

  async function finish() {
    if (!itemName.trim()) {
      toast.error("Cadastre o produto que voce quer vender.");
      setStep(2);
      return;
    }
    setBusy(true);
    try {
      const business = await createBusiness.mutateAsync({
        name: name.trim(),
        segment: segment.trim(),
        description: description.trim() || null,
        objectives: ["Vender"],
        differentiators: [],
      });
      queryClient.setQueryData(queryKeys.business, business);
      queryClient.invalidateQueries({ queryKey: queryKeys.session });

      const trimmedItem = itemName.trim();
      const price = itemPrice.trim() ? Number(itemPrice.replace(",", ".")) : null;
      const product = await productsApi.create({
        name: trimmedItem,
        price: price != null && !Number.isNaN(price) ? price : undefined,
      });
      if (photoFile) {
        const ticket = await assetsApi.createUploadUrl({
          filename: photoFile.name,
          mime_type: photoFile.type || "image/jpeg",
          size_bytes: photoFile.size,
          kind: "PRODUCT_PHOTO",
          product_id: product.id,
        });
        await uploadFileToSignedUrl(ticket, photoFile);
        const dimensions = await readImageDimensions(photoFile);
        await assetsApi.confirm(ticket.asset_id, {
          size_bytes: photoFile.size,
          width: dimensions?.width,
          height: dimensions?.height,
          analyze: false,
        });
      }

      const params = new URLSearchParams();
      params.set("product", product.id);
      if (destination) params.set("destination", destination);
      router.push(`/criar?${params.toString()}`);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Nao foi possivel terminar o cadastro.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-background px-4 py-10">
      <div className="mx-auto max-w-lg">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-lg shadow-brand-600/30">
            {step === 1 ? <Building2 className="h-6 w-6" /> : step === 2 ? <Package className="h-6 w-6" /> : <Sparkles className="h-6 w-6" />}
          </div>
          <p className="text-xs font-medium uppercase tracking-wide text-foreground/45">
            Passo {step} de 3
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-foreground">
            {step === 1 && "O que sua empresa faz?"}
            {step === 2 && "Qual produto voce vende?"}
            {step === 3 && "Onde quer publicar?"}
          </h1>
        </div>

        {step === 1 && (
          <div className="space-y-4 rounded-2xl border border-border-subtle bg-surface p-6">
            <div>
              <Label htmlFor="name">Nome do negocio *</Label>
              <Input id="name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Ex.: Cafeteria Aroma" />
              <FieldError>{nameError}</FieldError>
            </div>
            <div>
              <Label htmlFor="segment">Segmento *</Label>
              <Input id="segment" value={segment} onChange={(event) => setSegment(event.target.value)} placeholder="Ex.: Cafeteria e confeitaria" />
              <FieldError>{segmentError}</FieldError>
            </div>
            <div>
              <Label htmlFor="description">Descricao</Label>
              <Textarea
                id="description"
                rows={3}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="O que voce vende, como trabalha..."
              />
            </div>
            <Button size="lg" className="w-full" onClick={goFromStep1}>
              Continuar
            </Button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4 rounded-2xl border border-border-subtle bg-surface p-6">
            <div>
              <Label htmlFor="item_name">Nome do produto</Label>
              <Input
                id="item_name"
                value={itemName}
                onChange={(event) => setItemName(event.target.value)}
                placeholder="Ex.: Bolsa de couro caramelo"
              />
            </div>
            <div>
              <Label htmlFor="item_price">Preco (opcional)</Label>
              <Input
                id="item_price"
                inputMode="decimal"
                value={itemPrice}
                onChange={(event) => setItemPrice(event.target.value)}
                placeholder="Ex.: 42,90"
              />
            </div>
            <div>
              <Label htmlFor="item_photo">Foto (opcional)</Label>
              <input
                id="item_photo"
                type="file"
                accept="image/*"
                onChange={(event) => setPhotoFile(event.target.files?.[0] ?? null)}
                className="block w-full text-sm text-foreground/70"
              />
              <FieldHint>{photoFile ? photoFile.name : "JPG, PNG ou WebP."}</FieldHint>
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" className="flex-1" onClick={() => setStep(1)}>
                Voltar
              </Button>
              <Button variant="outline" className="flex-1" onClick={() => setStep(3)}>
                Pular
              </Button>
              <Button className="flex-1" onClick={() => setStep(3)}>
                Continuar
              </Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4 rounded-2xl border border-border-subtle bg-surface p-6">
            <div className="grid gap-2">
              {DESTINATIONS.map((entry) => (
                <button
                  key={entry.value}
                  type="button"
                  onClick={() => setDestination(entry.value)}
                  className={cn(
                    "rounded-xl border px-4 py-3 text-left",
                    destination === entry.value
                      ? "border-brand-500 bg-brand-50"
                      : "border-border-subtle hover:border-brand-200"
                  )}
                >
                  <p className="font-semibold text-foreground">{entry.label}</p>
                  <p className="mt-1 text-xs text-foreground/55">{entry.description}</p>
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" className="flex-1" onClick={() => setStep(2)}>
                Voltar
              </Button>
              <Button className="flex-1" onClick={() => void finish()} loading={busy}>
                Comecar a gerar
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
