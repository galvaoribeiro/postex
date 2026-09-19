"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

export function useSession() {
  return useQuery({
    queryKey: queryKeys.session,
    queryFn: authApi.me,
    retry: false,
    staleTime: 60_000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: authApi.login,
    onSuccess: (session) => {
      queryClient.setQueryData(queryKeys.session, session);
      toast.success(`Bem-vindo(a) de volta, ${session.user.full_name.split(" ")[0]}!`);
      router.push(session.has_business ? "/inicio" : "/business/new");
    },
    onError: (error: unknown) => {
      const message = error instanceof ApiError ? error.message : "Nao foi possivel entrar.";
      toast.error(message);
    },
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: authApi.register,
    onSuccess: (session) => {
      queryClient.setQueryData(queryKeys.session, session);
      toast.success("Conta criada! Vamos configurar o seu negocio.");
      router.push("/business/new");
    },
    onError: (error: unknown) => {
      const message = error instanceof ApiError ? error.message : "Nao foi possivel criar a conta.";
      toast.error(message);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      queryClient.clear();
      router.push("/login");
    },
  });
}
