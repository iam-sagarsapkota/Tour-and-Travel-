import { useId, useState } from "react"
import type { FormEvent, ReactNode } from "react"
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/lib/api"
import { safeNext } from "@/lib/safeNext"

import { useAuth } from "./AuthContext"

type Errors = Record<string, string | undefined>

function Field({
  label,
  name,
  error,
  hint,
  ...input
}: {
  label: string
  name: string
  error?: string
  hint?: string
} & React.ComponentProps<typeof Input>) {
  const id = useId()
  const describedBy = [error ? `${id}-error` : null, hint ? `${id}-hint` : null]
    .filter(Boolean)
    .join(" ")
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        name={name}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy || undefined}
        className="h-11"
        {...input}
      />
      {hint && !error && (
        <p id={`${id}-hint`} className="text-sm text-muted-foreground">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}

function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle: string
  children: ReactNode
  footer: ReactNode
}) {
  return (
    <div className="mx-auto w-full max-w-md px-4 py-12 sm:py-16">
      <div className="rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
        <h1 className="text-2xl font-bold text-forest">{title}</h1>
        <p className="mt-1 text-muted-foreground">{subtitle}</p>
        <div className="mt-6">{children}</div>
      </div>
      <p className="mt-6 text-center text-sm text-muted-foreground">{footer}</p>
    </div>
  )
}

function FormError({ message }: { message?: string }) {
  if (!message) return null
  return (
    <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
      {message}
    </p>
  )
}

/** Shared behaviour: where to go after auth, and the link to the sibling page. */
function useAuthFlow() {
  const [params] = useSearchParams()
  const rawNext = params.get("next")
  const destination = safeNext(rawNext)
  // Carry only a validated path over to the other form.
  const siblingQuery =
    rawNext && destination === rawNext ? `?next=${encodeURIComponent(rawNext)}` : ""
  return { destination, siblingQuery }
}

export function LoginPage() {
  const { login, status } = useAuth()
  const navigate = useNavigate()
  const { destination, siblingQuery } = useAuthFlow()
  const [errors, setErrors] = useState<Errors>({})
  const [submitting, setSubmitting] = useState(false)

  if (status === "authenticated") return <Navigate to={destination} replace />

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const identifier = String(data.get("identifier") ?? "").trim()
    const password = String(data.get("password") ?? "")

    const next: Errors = {}
    if (!identifier) next.identifier = "Enter your email or phone number."
    if (!password) next.password = "Enter your password."
    setErrors(next)
    if (Object.keys(next).length) return

    setSubmitting(true)
    try {
      await login(identifier, password)
      navigate(destination, { replace: true })
    } catch (error) {
      const message =
        error instanceof ApiError && error.code === "invalid_credentials"
          ? "Those details don't match an account. Check them and try again."
          : error instanceof ApiError && error.code === "throttled"
            ? "Too many attempts. Wait a minute and try again."
            : error instanceof ApiError
              ? error.message
              : "Something went wrong. Please try again."
      setErrors({ form: message })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Log in to see full trip details and book."
      footer={
        <>
          New here?{" "}
          <Link className="font-medium text-forest underline" to={`/register${siblingQuery}`}>
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <FormError message={errors.form} />
        <Field
          label="Email or phone number"
          name="identifier"
          autoComplete="username"
          error={errors.identifier}
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          error={errors.password}
        />
        <Button type="submit" className="h-11 w-full text-base" disabled={submitting}>
          {submitting ? "Logging in…" : "Log in"}
        </Button>
      </form>
    </AuthShell>
  )
}

export function RegisterPage() {
  const { register, status } = useAuth()
  const navigate = useNavigate()
  const { destination, siblingQuery } = useAuthFlow()
  const [errors, setErrors] = useState<Errors>({})
  const [submitting, setSubmitting] = useState(false)

  if (status === "authenticated") return <Navigate to={destination} replace />

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const value = (name: string) => String(data.get(name) ?? "")
    const fullName = value("full_name").trim()
    const email = value("email").trim()
    const phone = value("phone").trim()
    const password = value("password")
    const confirm = value("password_confirm")

    const next: Errors = {}
    if (!fullName) next.full_name = "Enter your full name."
    if (!email && !phone) next.email = "Enter an email or a phone number (at least one)."
    if (password.length < 8) next.password = "Use at least 8 characters."
    if (password !== confirm) next.password_confirm = "Passwords do not match."
    setErrors(next)
    if (Object.keys(next).length) return

    setSubmitting(true)
    try {
      await register({
        full_name: fullName,
        password,
        password_confirm: confirm,
        ...(email ? { email } : {}),
        ...(phone ? { phone } : {}),
      })
      navigate(destination, { replace: true })
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors({
          full_name: error.first("full_name"),
          email: error.first("email"),
          phone: error.first("phone"),
          password: error.first("password"),
          password_confirm: error.first("password_confirm"),
          form:
            error.formError ?? (Object.keys(error.fieldErrors).length ? undefined : error.message),
        })
      } else {
        setErrors({ form: "Something went wrong. Please try again." })
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Register to view full trip details and book your trek."
      footer={
        <>
          Already have an account?{" "}
          <Link className="font-medium text-forest underline" to={`/login${siblingQuery}`}>
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <FormError message={errors.form} />
        <Field label="Full name" name="full_name" autoComplete="name" error={errors.full_name} />
        <Field
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          error={errors.email}
          hint="Email or phone number - at least one is required."
        />
        <Field
          label="Phone number"
          name="phone"
          type="tel"
          autoComplete="tel"
          placeholder="+977 98XXXXXXXX"
          error={errors.phone}
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          error={errors.password}
          hint="At least 8 characters."
        />
        <Field
          label="Confirm password"
          name="password_confirm"
          type="password"
          autoComplete="new-password"
          error={errors.password_confirm}
        />
        <Button type="submit" className="h-11 w-full text-base" disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </Button>
      </form>
    </AuthShell>
  )
}
