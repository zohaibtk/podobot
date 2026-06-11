import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { PodoBotBrand } from "@/design-system/components/PodoBotBrand";
import { useAuth } from "@/features/auth/hooks";

const loginSchema = z.object({
  email: z.string().trim().email("A valid email address is required").max(240),
  password: z.string().min(1, "Password is required").max(240)
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();
  const navigate = useNavigate();
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    mode: "onChange",
    defaultValues: {
      email: "",
      password: ""
    }
  });

  async function submit(values: LoginFormValues) {
    setError(null);
    try {
      await login(values.email, values.password);
      navigate("/dashboard", { replace: true });
    } catch (loginError) {
      setError(errorMessage(loginError));
    }
  }

  return (
    <main className="streamly-theme min-h-screen bg-streamly-paper text-streamly-coal">
      <div className="grid min-h-screen lg:grid-cols-[minmax(0,1fr)_minmax(28rem,34rem)]">
        <section className="relative hidden overflow-hidden bg-streamly-coal px-10 py-10 text-center text-white lg:flex lg:flex-col lg:items-center lg:justify-center lg:gap-16">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_22%_20%,rgba(154,110,255,0.55),transparent_32%),linear-gradient(135deg,rgba(238,231,255,0.22),rgba(74,54,131,0.92))]" />
          <div className="relative z-10">
            <PodoBotBrand className="mx-auto w-full max-w-[38rem] justify-center" tone="light" />
          </div>

          <div className="relative z-10 max-w-2xl">
            <p className="streamly-kicker text-white/70">Executive podcast operations</p>
            <h1 className="mt-4 font-streamly-platform text-5xl font-extrabold leading-tight">
              Sign in to the production workspace.
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-base font-semibold leading-7 text-white/76">
              Coordinate series planning, editorial approvals, media readiness,
              captions, publishing, and access controls from one secured cockpit.
            </p>
          </div>

        </section>

        <section className="flex items-center justify-center px-5 py-10 sm:px-8">
          <div className="w-full max-w-md">
            <div className="mb-8 lg:hidden">
              <PodoBotBrand className="mx-auto w-full max-w-xs" />
            </div>

            <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-6 shadow-streamly-card">
              <div>
                <p className="streamly-kicker">Secure access</p>
                <h2 className="mt-2 font-streamly-platform text-3xl font-extrabold text-streamly-coal">
                  Welcome back
                </h2>
                <p className="mt-2 text-sm font-bold leading-6 text-streamly-purpleBlue">
                  Use your workspace credentials to continue.
                </p>
              </div>

              <form className="mt-6 space-y-4" onSubmit={(event) => void handleSubmit(submit)(event)}>
                <label className="grid gap-2">
                  <span className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
                    Email
                  </span>
                  <span className="relative">
                    <Mail
                      aria-hidden
                      className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--streamly-text-muted)]"
                    />
                    <input
                      autoComplete="email"
                      className="streamly-search w-full max-w-none pl-9"
                      placeholder="admin@podobot.com"
                      type="email"
                      {...register("email")}
                    />
                  </span>
                  {errors.email ? (
                    <span className="text-xs font-bold text-red-600">{errors.email.message}</span>
                  ) : null}
                </label>

                <label className="grid gap-2">
                  <span className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
                    Password
                  </span>
                  <span className="relative">
                    <LockKeyhole
                      aria-hidden
                      className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--streamly-text-muted)]"
                    />
                    <input
                      autoComplete="current-password"
                      className="streamly-search w-full max-w-none pl-9 pr-11"
                      type={showPassword ? "text" : "password"}
                      {...register("password")}
                    />
                    <button
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      className="absolute right-2 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-streamly-pill text-streamly-purpleBlue transition hover:bg-streamly-lavender"
                      onClick={() => setShowPassword((value) => !value)}
                      type="button"
                    >
                      {showPassword ? (
                        <EyeOff aria-hidden className="h-4 w-4" />
                      ) : (
                        <Eye aria-hidden className="h-4 w-4" />
                      )}
                    </button>
                  </span>
                  {errors.password ? (
                    <span className="text-xs font-bold text-red-600">
                      {errors.password.message}
                    </span>
                  ) : null}
                </label>

                {error ? (
                  <div className="rounded-streamly-lg border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700">
                    {error}
                  </div>
                ) : null}

                <button
                  className="streamly-button-primary h-11 w-full justify-center disabled:opacity-60"
                  disabled={isSubmitting}
                  type="submit"
                >
                  {isSubmitting ? "Signing in..." : "Sign in"}
                  <ArrowRight aria-hidden className="h-4 w-4" />
                </button>
              </form>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Sign in failed.";
}
