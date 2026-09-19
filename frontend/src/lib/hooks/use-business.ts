"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { businessApi } from "@/lib/api/business";
import { ApiError } from "@/lib/api/client";
import type { BusinessUpdatePayload } from "@/lib/api/types";
import { queryKeys } from "@/lib/query-keys";

export function useBusiness(enabled = true) {
  return useQuery({
    queryKey: queryKeys.business,
    queryFn: businessApi.current,
    enabled,
    retry: false,
  });
}

export function useUpdateBusiness() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BusinessUpdatePayload) => businessApi.updateCurrent(payload),
    onSuccess: (business) => {
      queryClient.setQueryData(queryKeys.business, business);
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
      toast.success("Negocio atualizado.");
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : "Nao foi possivel salvar.");
    },
  });
}
