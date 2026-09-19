"use client";

import {
  CreditCard,
  Image as ImageIcon,
  Lightbulb,
  Share2,
  Store,
  User,
} from "lucide-react";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const ITEMS: {
  href?: string;
  label: string;
  description: string;
  icon: LucideIcon;
  disabled?: boolean;
}[] = [
  {
    href: "/settings/negocio",
    label: "Negocio",
    description: "Dados da empresa, produtos e servicos.",
    icon: Store,
  },
  {
    href: "/settings/imagens",
    label: "Imagens",
    description: "Fotos de produto, lugar e referencias.",
    icon: ImageIcon,
  },
  {
    href: "/settings/ideias",
    label: "Ideias",
    description: "Geracao avulsa de ideias. Sem polimento extra.",
    icon: Lightbulb,
  },
  {
    href: "/settings/conta",
    label: "Conta",
    description: "Perfil, senha e motor de IA.",
    icon: User,
  },
  {
    label: "Instagram",
    description: "Publicacao automatica ainda nao esta disponivel.",
    icon: Share2,
    disabled: true,
  },
  {
    label: "Plano",
    description: "Cobranca e limites entram depois do MVP.",
    icon: CreditCard,
    disabled: true,
  },
];

export default function SettingsIndexPage() {
  return (
    <div>
      <PageHeader
        title="Configuracoes"
        description="O que saiu do menu diario mora aqui. O fluxo do dia a dia e Inicio e Criar."
      />
      <div className="grid gap-3 sm:grid-cols-2">
        {ITEMS.map((item) => {
          const Icon = item.icon;
          const body = (
            <Card
              className={cn(
                "h-full transition-colors",
                item.disabled ? "opacity-55" : "hover:border-brand-200 hover:bg-brand-50/30"
              )}
            >
              <CardContent className="flex items-start gap-3 p-5">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                  <Icon className="h-5 w-5" />
                </span>
                <div>
                  <p className="font-semibold text-foreground">{item.label}</p>
                  <p className="mt-1 text-sm text-foreground/55">{item.description}</p>
                </div>
              </CardContent>
            </Card>
          );
          if (!item.href || item.disabled) {
            return <div key={item.label}>{body}</div>;
          }
          return (
            <Link key={item.href} href={item.href}>
              {body}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
