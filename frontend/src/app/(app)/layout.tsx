"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { PageSpinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api/client";
import { useBusiness } from "@/lib/hooks/use-business";
import { useSession } from "@/lib/hooks/use-session";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: session, isLoading: sessionLoading, isError, error } = useSession();
  const { data: business, isLoading: businessLoading } = useBusiness(Boolean(session?.has_business));

  useEffect(() => {
    if (isError && error instanceof ApiError && error.status === 401) {
      router.replace("/login");
    }
  }, [isError, error, router]);

  useEffect(() => {
    if (session && !session.has_business) {
      router.replace("/business/new");
    }
  }, [session, router]);

  if (isError) {
    return <PageSpinner label="Sessao expirada. Redirecionando..." />;
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
