import { NextResponse, type NextRequest } from "next/server";

// Mesmo nome usado em `backend/app/core/deps.py` (ACCESS_TOKEN_COOKIE).
const ACCESS_TOKEN_COOKIE = "mdc_access_token";
const REFRESH_TOKEN_COOKIE = "mdc_refresh_token";

const PUBLIC_PATHS = ["/login", "/register"];

/**
 * Guarda de rota "rasa": so verifica se existe algum cookie de sessao.
 * A validacao de verdade (token expirado, usuario inativo, etc.) acontece no
 * backend a cada chamada; isso apenas evita a piscada de redirecionamento
 * para quem claramente nao tem sessao.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = Boolean(
    request.cookies.get(ACCESS_TOKEN_COOKIE) || request.cookies.get(REFRESH_TOKEN_COOKIE)
  );

  const isPublicPath = PUBLIC_PATHS.some((path) => pathname.startsWith(path));

  if (!hasSession && !isPublicPath && pathname !== "/") {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (hasSession && isPublicPath) {
    const url = request.nextUrl.clone();
    url.pathname = "/inicio";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
