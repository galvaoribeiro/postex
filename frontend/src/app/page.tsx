import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export default async function RootPage() {
  const store = await cookies();
  const hasSession = Boolean(store.get("mdc_access_token") || store.get("mdc_refresh_token"));
  redirect(hasSession ? "/dashboard" : "/login");
}
