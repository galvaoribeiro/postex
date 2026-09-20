import { api } from "./client";
import type { AssetKind, AssetRead, AssetStatus, AssetUploadResponse } from "./types";

export const assetsApi = {
  list: (filters?: {
    kind?: AssetKind;
    status?: AssetStatus;
    productId?: string;
    serviceId?: string;
  }) =>
    api.get<AssetRead[]>("/assets", {
      query: {
        kind: filters?.kind,
        status: filters?.status,
        product_id: filters?.productId,
        service_id: filters?.serviceId,
      },
    }),
  get: (id: string) => api.get<AssetRead>(`/assets/${id}`),
  createUploadUrl: (payload: {
    filename: string;
    mime_type: string;
    size_bytes?: number;
    kind: AssetKind;
    title?: string;
    alt_text?: string;
    tags?: string[];
    product_id?: string | null;
    service_id?: string | null;
  }) => api.post<AssetUploadResponse>("/assets/upload-url", payload),
  confirm: (
    id: string,
    payload: { size_bytes?: number; width?: number; height?: number; analyze?: boolean }
  ) => api.post<AssetRead>(`/assets/${id}/confirm`, payload),
  analyze: (id: string) =>
    api.post<{ job_id: string; asset_id: string }>(`/assets/${id}/analyze`),
  update: (
    id: string,
    payload: Partial<{
      kind: AssetKind;
      title: string | null;
      alt_text: string | null;
      tags: string[];
      product_id: string | null;
      service_id: string | null;
    }>
  ) => api.patch<AssetRead>(`/assets/${id}`, payload),
  remove: (id: string) => api.delete<{ message: string }>(`/assets/${id}`),
};

/** Faz upload direto ao storage usando a URL assinada emitida pela API. */
export async function uploadFileToSignedUrl(
  upload: AssetUploadResponse,
  file: File
): Promise<void> {
  const response = await fetch(upload.upload_url, {
    method: upload.method || "PUT",
    headers: { "Content-Type": file.type, ...upload.headers },
    body: file,
  });
  if (!response.ok) {
    throw new Error(`Falha ao enviar o arquivo para o storage (status ${response.status}).`);
  }
}

/** Sobe uma foto e liga ao produto/servico. A API nunca recebe o binario. */
export async function uploadLinkedImage(
  file: File,
  options: {
    kind?: AssetKind;
    productId?: string | null;
    serviceId?: string | null;
  } = {}
): Promise<AssetRead> {
  const ticket = await assetsApi.createUploadUrl({
    filename: file.name,
    mime_type: file.type || "image/jpeg",
    size_bytes: file.size,
    kind: options.kind ?? "PRODUCT_PHOTO",
    product_id: options.productId,
    service_id: options.serviceId,
  });
  await uploadFileToSignedUrl(ticket, file);
  const dimensions = await readImageDimensions(file);
  return assetsApi.confirm(ticket.asset_id, {
    size_bytes: file.size,
    width: dimensions?.width,
    height: dimensions?.height,
    analyze: false,
  });
}

export function readImageDimensions(file: File): Promise<{ width: number; height: number } | null> {
  if (!file.type.startsWith("image/")) return Promise.resolve(null);
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      resolve({ width: img.naturalWidth, height: img.naturalHeight });
      URL.revokeObjectURL(url);
    };
    img.onerror = () => {
      resolve(null);
      URL.revokeObjectURL(url);
    };
    img.src = url;
  });
}
