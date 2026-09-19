import { Sparkles } from "lucide-react";
import type { ReactNode } from "react";

export function AuthLayout({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 via-background to-background px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-lg shadow-brand-600/30">
            <Sparkles className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-semibold text-foreground">{title}</h1>
          <p className="mt-1 text-sm text-foreground/55">{description}</p>
        </div>
        <div className="rounded-2xl border border-border-subtle bg-surface p-6 shadow-sm sm:p-8">
          {children}
        </div>
        {footer && <div className="mt-6 text-center text-sm text-foreground/55">{footer}</div>}
      </div>
    </div>
  );
}
