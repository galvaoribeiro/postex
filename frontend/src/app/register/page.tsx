"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthLayout } from "@/components/layout/auth-layout";
import { Button } from "@/components/ui/button";
import { FieldError, Input, Label } from "@/components/ui/input";
import { useRegister } from "@/lib/hooks/use-session";

const schema = z.object({
  full_name: z.string().min(2, "Informe seu nome.").max(160),
  email: z.string().email("Informe um e-mail valido."),
  password: z
    .string()
    .min(8, "A senha deve ter ao menos 8 caracteres.")
    .max(128)
    .refine(
      (value) => !(/^\d+$/.test(value) || /^[A-Za-z]+$/.test(value)),
      "A senha deve combinar letras e numeros."
    ),
});

type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const register_ = useRegister();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  return (
    <AuthLayout
      title="Criar sua conta"
      description="Comece a manter o Instagram do seu negocio sempre ativo"
      footer={
        <>
          Ja tem conta?{" "}
          <Link href="/login" className="font-medium text-brand-600 hover:underline">
            Entrar
          </Link>
        </>
      }
    >
      <form className="space-y-4" onSubmit={handleSubmit((values) => register_.mutate(values))}>
        <div>
          <Label htmlFor="full_name">Nome completo</Label>
          <Input id="full_name" placeholder="Seu nome" {...register("full_name")} />
          <FieldError>{errors.full_name?.message}</FieldError>
        </div>
        <div>
          <Label htmlFor="email">E-mail</Label>
          <Input id="email" type="email" placeholder="voce@empresa.com" {...register("email")} />
          <FieldError>{errors.email?.message}</FieldError>
        </div>
        <div>
          <Label htmlFor="password">Senha</Label>
          <Input id="password" type="password" placeholder="Minimo 8 caracteres" {...register("password")} />
          <FieldError>{errors.password?.message}</FieldError>
        </div>
        <Button type="submit" className="w-full" loading={register_.isPending}>
          Criar conta
        </Button>
      </form>
    </AuthLayout>
  );
}
