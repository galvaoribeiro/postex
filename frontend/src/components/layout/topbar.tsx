"use client";

import { LogOut, Menu, Settings, User, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { NAV_ITEMS } from "@/components/layout/sidebar";
import { useLogout, useSession } from "@/lib/hooks/use-session";
import { cn, initials } from "@/lib/utils";
import type { BusinessRead } from "@/lib/api/types";

export function Topbar({ business }: { business?: BusinessRead | null }) {
  const { data: session } = useSession();
  const logout = useLogout();
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const pathname = usePathname();

  return (
    <header className="flex h-16 items-center justify-between gap-4 border-b border-border-subtle bg-surface px-4 lg:px-8">
      <div className="flex items-center gap-3">
        <button
          className="rounded-lg p-2 text-foreground/60 hover:bg-surface-muted lg:hidden"
          onClick={() => setMobileNavOpen(true)}
          aria-label="Abrir menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        {business && (
          <div className="hidden flex-col sm:flex">
            <span className="text-sm font-semibold text-foreground">{business.name}</span>
            <span className="text-xs text-foreground/45">{business.segment}</span>
          </div>
        )}
      </div>

      <div className="relative">
        <button
          onClick={() => setMenuOpen((prev) => !prev)}
          className="flex items-center gap-2 rounded-full border border-border-subtle bg-surface-muted py-1 pl-1 pr-3 transition-colors hover:bg-border-subtle"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold text-white">
            {initials(session?.user.full_name)}
          </span>
          <span className="hidden text-sm font-medium text-foreground sm:inline">
            {session?.user.full_name?.split(" ")[0]}
          </span>
        </button>

        {menuOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
            <div className="absolute right-0 z-20 mt-2 w-56 overflow-hidden rounded-xl border border-border-subtle bg-surface shadow-lg">
              <div className="border-b border-border-subtle px-4 py-3">
                <p className="text-sm font-medium text-foreground">{session?.user.full_name}</p>
                <p className="text-xs text-foreground/50">{session?.user.email}</p>
              </div>
              <Link
                href="/settings"
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 px-4 py-2.5 text-sm text-foreground/80 hover:bg-surface-muted"
              >
                <User className="h-4 w-4" /> Meu perfil
              </Link>
              <Link
                href="/business"
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 px-4 py-2.5 text-sm text-foreground/80 hover:bg-surface-muted"
              >
                <Settings className="h-4 w-4" /> Configurar negocio
              </Link>
              <button
                onClick={() => logout.mutate()}
                className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-danger-fg hover:bg-danger-bg"
              >
                <LogOut className="h-4 w-4" /> Sair
              </button>
            </div>
          </>
        )}
      </div>

      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileNavOpen(false)} />
          <div className="absolute left-0 top-0 flex h-full w-72 flex-col bg-surface p-4 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <span className="text-sm font-semibold text-brand-600">Motor de Conteudo</span>
              <button onClick={() => setMobileNavOpen(false)} aria-label="Fechar">
                <X className="h-5 w-5 text-foreground/60" />
              </button>
            </div>
            <nav className="flex flex-col gap-1">
              {NAV_ITEMS.map((item) => {
                const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileNavOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium",
                      active ? "bg-brand-50 text-brand-700" : "text-foreground/70 hover:bg-surface-muted"
                    )}
                  >
                    <Icon className="h-[18px] w-[18px]" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>
      )}
    </header>
  );
}
