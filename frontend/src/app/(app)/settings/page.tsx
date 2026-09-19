"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cpu, LogOut, ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FieldError, Input, Label } from "@/components/ui/input";
import { aiApi } from "@/lib/api/ai";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { useLogout, useSession } from "@/lib/hooks/use-session";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";

const profileSchema = z.object({
  full_name: z.string().min(2, "Informe seu nome.").max(160),
});
type ProfileValues = z.infer<typeof profileSchema>;

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Informe a senha atual."),
    new_password: z
      .string()
      .min(8, "A nova senha deve ter ao menos 8 caracteres.")
      .max(128)
      .refine(
        (value) => !(/^\d+$/.test(value) || /^[A-Za-z]+$/.test(value)),
        "A senha deve combinar letras e numeros."
      ),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "As senhas nao coincidem.",
    path: ["confirm_password"],
  });
type PasswordValues = z.infer<typeof passwordSchema>;

export default function SettingsPage() {
  const { data: session } = useSession();
  const queryClient = useQueryClient();
  const logout = useLogout();

  const { data: capabilities } = useQuery({
    queryKey: queryKeys.capabilities,
    queryFn: aiApi.capabilities,
  });

  const profileForm = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    values: { full_name: session?.user.full_name ?? "" },
  });

  const passwordForm = useForm<PasswordValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  const updateProfile = useMutation({
    mutationFn: authApi.updateProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.session });
      toast.success("Perfil atualizado.");
    },
    onError: (error: unknown) => toast.error(error instanceof ApiError ? error.message : "Erro ao atualizar perfil."),
  });

  const changePassword = useMutation({
    mutationFn: authApi.changePassword,
    onSuccess: () => {
      toast.success("Senha alterada. Faca login novamente.");
      passwordForm.reset();
      logout.mutate();
    },
    onError: (error: unknown) => toast.error(error instanceof ApiError ? error.message : "Erro ao alterar senha."),
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Configuracoes" description="Sua conta e as capacidades de IA disponiveis." />

      <Card>
        <CardHeader>
          <CardTitle>Perfil</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-4"
            onSubmit={profileForm.handleSubmit((values) => updateProfile.mutate(values))}
          >
            <div>
              <Label htmlFor="full_name">Nome completo</Label>
              <Input id="full_name" {...profileForm.register("full_name")} />
              <FieldError>{profileForm.formState.errors.full_name?.message}</FieldError>
            </div>
            <div>
              <Label>E-mail</Label>
              <Input value={session?.user.email ?? ""} disabled />
            </div>
            <p className="text-xs text-foreground/45">
              Conta criada em {formatDate(session?.user.created_at)}
            </p>
            <div className="flex justify-end">
              <Button type="submit" loading={updateProfile.isPending}>
                Salvar
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-brand-600" /> Alterar senha
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-4"
            onSubmit={passwordForm.handleSubmit((values) => changePassword.mutate(values))}
          >
            <div>
              <Label htmlFor="current_password">Senha atual</Label>
              <Input id="current_password" type="password" {...passwordForm.register("current_password")} />
              <FieldError>{passwordForm.formState.errors.current_password?.message}</FieldError>
            </div>
            <div>
              <Label htmlFor="new_password">Nova senha</Label>
              <Input id="new_password" type="password" {...passwordForm.register("new_password")} />
              <FieldError>{passwordForm.formState.errors.new_password?.message}</FieldError>
            </div>
            <div>
              <Label htmlFor="confirm_password">Confirmar nova senha</Label>
              <Input id="confirm_password" type="password" {...passwordForm.register("confirm_password")} />
              <FieldError>{passwordForm.formState.errors.confirm_password?.message}</FieldError>
            </div>
            <div className="flex justify-end">
              <Button type="submit" variant="outline" loading={changePassword.isPending}>
                Alterar senha
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {capabilities && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-brand-600" /> Motor de IA
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
            <InfoItem label="Provedor" value={capabilities.provider} />
            <InfoItem label="Modelo" value={capabilities.model} />
            <InfoItem label="Execucao" value={capabilities.execution_mode} />
            <InfoItem label="Visao computacional" value={capabilities.supports_vision ? "Sim" : "Nao"} />
            <InfoItem label="Ideias por lote (padrao)" value={String(capabilities.default_idea_count)} />
            <InfoItem label="Taxonomia" value={`v${capabilities.taxonomy_version}`} />
          </CardContent>
        </Card>
      )}

      <Card className="border-danger-bg">
        <CardContent className="flex items-center justify-between p-5">
          <div>
            <p className="font-medium text-foreground">Sair da conta</p>
            <p className="text-sm text-foreground/55">Voce precisara fazer login novamente.</p>
          </div>
          <Button variant="danger" icon={<LogOut className="h-4 w-4" />} onClick={() => logout.mutate()}>
            Sair
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-surface-muted p-3">
      <p className="text-xs text-foreground/45">{label}</p>
      <p className="mt-0.5 font-medium text-foreground">
        <Badge tone="brand">{value}</Badge>
      </p>
    </div>
  );
}
