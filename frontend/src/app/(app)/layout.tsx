"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { PageSpinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api/client";
import { useBusiness } from "@/lib/hooks/use-business";
import { useSession } from "@/lib/hooks/use-session";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const {
    data: session,
    isLoading: sessionLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useSession();
  const { data: business, isLoading: businessLoading } = useBusiness(Boolean(session?.has_business));
  const unauthorized = isError && error instanceof ApiError && error.status === 401;

  useEffect(() => {
    if (unauthorized) {
      router.replace("/login");
    }
  }, [unauthorized, router]);

  useEffect(() => {
    if (session && !session.has_business) {
      router.replace("/business/new");
    }
  }, [session, router]);

  if (unauthorized) {
    return <PageSpinner label="Sessao expirada. Redirecionando..." />;
  }

  if (isError) {
    return (
      <div className="flex min-h-64 flex-col items-center justify-center gap-4 px-6 text-center">
        <p className="text-sm text-foreground/70">
          Nao foi possivel falar com a API. Confira se o container <code>api</code> esta no ar e
          tente de novo.
        </p>
        <Button onClick={() => void refetch()} loading={isFetching}>
          Tentar novamente
        </Button>
      </div>
    );
  }

  if (sessionLoading || !session) {
    return <PageSpinner label="Carregando sua conta..." />;
  }

  if (!session.has_business) {
    return <PageSpinner label="Preparando onboarding..." />;
  }

  if (businessLoading || !business) {
    return <PageSpinner label="Carregando seu negocio..." />;
  }

  return <AppShell business={business}>{children}</AppShell>;
}
