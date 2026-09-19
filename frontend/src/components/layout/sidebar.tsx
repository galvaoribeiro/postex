"use client";

import {
  Boxes,
  CalendarDays,
  Image as ImageIcon,
  LayoutDashboard,
  Lightbulb,
  Notebook,
  Settings,
  Sparkles,
  Store,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

export const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/business", label: "Meu Negocio", icon: Store },
  { href: "/products", label: "Produtos", icon: Boxes },
  { href: "/services", label: "Servicos", icon: Wrench },
  { href: "/assets", label: "Biblioteca de Imagens", icon: ImageIcon },
  { href: "/ideas", label: "Ideias", icon: Lightbulb },
  { href: "/contents", label: "Conteudos", icon: Notebook },
  { href: "/calendar", label: "Calendario", icon: CalendarDays },
  { href: "/settings", label: "Configuracoes", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border-subtle bg-surface lg:flex">
      <div className="flex h-16 items-center gap-2 px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white">
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight text-foreground">Motor de</p>
          <p className="text-sm font-semibold leading-tight text-brand-600">Conteudo</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4 scrollbar-thin">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-brand-50 text-brand-700"
                  : "text-foreground/60 hover:bg-surface-muted hover:text-foreground"
              )}
            >
              <Icon className="h-[18px] w-[18px]" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border-subtle px-6 py-4 text-xs text-foreground/40">
        Motor de Conteudo &copy; {new Date().getFullYear()}
      </div>
    </aside>
  );
}
