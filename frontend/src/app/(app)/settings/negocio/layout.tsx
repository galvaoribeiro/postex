"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

const TABS = [
  { href: "/settings/negocio", label: "Negocio" },
  { href: "/settings/negocio/produtos", label: "Produtos" },
];

export default function NegocioLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div>
      <div className="mb-6 flex flex-wrap gap-2">
        {TABS.map((tab) => {
          const active =
            tab.href === "/settings/negocio"
              ? pathname === tab.href
              : pathname.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                active
                  ? "border-brand-500 bg-brand-50 text-brand-700"
                  : "border-border-subtle text-foreground/60 hover:border-brand-200"
              )}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
      {children}
    </div>
  );
}
