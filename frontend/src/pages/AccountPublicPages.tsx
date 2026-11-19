import { CheckCircle2Icon } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import type { FormEvent } from "react"
import { Link, useSearchParams } from "react-router-dom"

import { AuthShell, Field, FormError } from "@/components/forms"
import type { Errors } from "@/components/forms"
import { ErrorState } from "@/components/States"
import { Button, buttonVariants } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { useSiteSettings } from "@/features/account/queries"
import { useAuth } from "@/features/auth/AuthContext"
import { api, ApiError } from "@/lib/api"

function apiErrors(error: unknown, names: string[]): Errors {
  if (!(error instanceof ApiError)) return { form: "Something went wrong. Please try again." }
  const errors: Errors = { form: error.formError }
  for (const name of names) errors[name] = error.first(name)
  if (!Object.values(errors).some(Boolean)) errors.form = error.message
  return errors
}

export function ForgotPasswordPage() {
  const [sent, setSent] = useState(false)
  const [errors, setErrors] = useState<Errors>({})
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const email = String(new FormData(event.currentTarget).get("email") ?? "").trim()
    if (!email) {
      setErrors({ email: "Enter the email you registered with." })
      return
    }
    setSubmitting(true)
    try {
      await api("/auth/password/reset/", { method: "POST", body: { email }, auth: false })
      setSent(true)
    } catch (error) {
      setErrors(apiErrors(error, ["email"]))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Forgot your password?"
      subtitle="We'll email you a link to choose a new one."
      footer={
        <Link className="font-medium text-forest underline" to="/login">
          Back to log in
        </Link>
      }
    >
      {sent ? (
        <p role="status" className="rounded-lg bg-emerald-50 p-4 text-sm text-emerald-950">
          If an account exists for that email, a reset link is on its way. It expires in an hour.
        </p>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-4">
          <FormError message={errors.form} />
          <Field
            label="Email"
            name="email"
            type="email"
            autoComplete="email"
            error={errors.email}
          />
          <p className="text-sm text-muted-foreground">
            Registered with a phone number only? Contact us and we'll help you reset it.
          </p>
          <Button type="submit" className="h-11 w-full text-base" disabled={submitting}>
            {submitting ? "Sending…" : "Send reset link"}
          </Button>
        </form>
      )}
    </AuthShell>
  )
}

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const uid = params.get("uid") ?? ""
  const token = params.get("token") ?? ""
  const [done, setDone] = useState(false)
  const [errors, setErrors] = useState<Errors>({})
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const password = String(data.get("new_password") ?? "")
    const confirm = String(data.get("new_password_confirm") ?? "")
    const local: Errors = {}
    if (password.length < 8) local.new_password = "Use at least 8 characters."
    if (password !== confirm) local.new_password_confirm = "Passwords do not match."
    setErrors(local)
    if (Object.keys(local).length) return
    setSubmitting(true)
    try {
      await api("/auth/password/reset/confirm/", {
        method: "POST",
        body: { uid, token, new_password: password, new_password_confirm: confirm },
        auth: false,
      })
      setDone(true)
    } catch (error) {
      const found = apiErrors(error, ["new_password", "new_password_confirm", "token"])
      if (found.token) found.form = found.token
      setErrors(found)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Choose a new password"
      subtitle="Your old password stops working and other devices are signed out."
      footer={
        <Link className="font-medium text-forest underline" to="/forgot-password">
          Need a new link?
        </Link>
      }
    >
      {done ? (
        <div role="status" className="space-y-4">
          <p className="rounded-lg bg-emerald-50 p-4 text-sm text-emerald-950">
            Your password has been changed.
          </p>
          <Link to="/login" className={buttonVariants({ className: "h-11 w-full" })}>
            Log in
          </Link>
        </div>
      ) : !uid || !token ? (
        <p className="text-sm text-destructive">
          This reset link is incomplete. Request a new one.
        </p>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-4">
          <FormError message={errors.form} />
          <Field
            label="New password"
            name="new_password"
            type="password"
            autoComplete="new-password"
            error={errors.new_password}
            hint="At least 8 characters."
          />
          <Field
            label="Confirm new password"
            name="new_password_confirm"
            type="password"
            autoComplete="new-password"
            error={errors.new_password_confirm}
          />
          <Button type="submit" className="h-11 w-full text-base" disabled={submitting}>
            {submitting ? "Saving…" : "Set new password"}
          </Button>
        </form>
      )}
    </AuthShell>
  )
}

export function VerifyEmailPage() {
  const [params] = useSearchParams()
  const token = params.get("token") ?? ""
  const { status, refreshUser } = useAuth()
  const [state, setState] = useState<"working" | "done" | "failed">(token ? "working" : "failed")
  const started = useRef(false)

  useEffect(() => {
    if (!token || started.current) return
    started.current = true // the link is single-purpose; don't post it twice in StrictMode
    api("/auth/verify-email/", { method: "POST", body: { token }, auth: false })
      .then(() => setState("done"))
      .catch(() => setState("failed"))
  }, [token])

  useEffect(() => {
    if (state === "done" && status === "authenticated") void refreshUser()
  }, [state, status, refreshUser])

  return (
    <AuthShell
      title="Email verification"
      subtitle="Confirming the address on your account."
      footer={
        <Link className="font-medium text-forest underline" to="/dashboard/profile">
          Go to your profile
        </Link>
      }
    >
      {state === "working" && <p role="status">Checking your link…</p>}
      {state === "done" && (
        <p role="status" className="flex items-center gap-2 font-semibold text-success">
          <CheckCircle2Icon className="size-5" aria-hidden="true" /> Your email is verified.
        </p>
      )}
      {state === "failed" && (
        <p role="alert" className="text-sm text-destructive">
          This link is invalid or has expired. Send a new one from your profile.
        </p>
      )}
    </AuthShell>
  )
}

export function ContactPage() {
  const site = useSiteSettings()
  const [sent, setSent] = useState(false)
  const [errors, setErrors] = useState<Errors>({})
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const value = (name: string) => String(data.get(name) ?? "").trim()
    const body = {
      name: value("name"),
      email: value("email"),
      phone: value("phone"),
      subject: value("subject"),
      message: value("message"),
    }
    const local: Errors = {}
    if (!body.name) local.name = "Enter your name."
    if (!body.email) local.email = "Enter your email so we can reply."
    if (!body.subject) local.subject = "Add a subject."
    if (!body.message) local.message = "Write your message."
    setErrors(local)
    if (Object.keys(local).length) return
    setSubmitting(true)
    try {
      await api("/contact/", { method: "POST", body, auth: false })
      setSent(true)
    } catch (error) {
      setErrors(apiErrors(error, ["name", "email", "phone", "subject", "message"]))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-10 px-4 py-12 md:grid-cols-[1fr_18rem]">
      <div>
        <h1 className="text-3xl font-extrabold text-forest">Contact us</h1>
        <p className="mt-2 text-muted-foreground">
          Questions about a trek, a private group or your booking? We usually reply within a day.
        </p>
        <div className="mt-6 rounded-2xl border bg-card p-6">
          {sent ? (
            <p role="status" className="font-semibold text-success">
              Thank you. Your message has been sent.
            </p>
          ) : (
            <form onSubmit={submit} noValidate className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <FormError message={errors.form} />
              </div>
              <Field label="Your name" name="name" autoComplete="name" error={errors.name} />
              <Field
                label="Email"
                name="email"
                type="email"
                autoComplete="email"
                error={errors.email}
              />
              <Field
                label="Phone (optional)"
                name="phone"
                type="tel"
                autoComplete="tel"
                error={errors.phone}
              />
              <Field label="Subject" name="subject" error={errors.subject} />
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="contact-message">Message</Label>
                <textarea
                  id="contact-message"
                  name="message"
                  rows={6}
                  maxLength={5000}
                  aria-invalid={errors.message ? true : undefined}
                  aria-describedby={errors.message ? "contact-message-error" : undefined}
                  className="w-full rounded-lg border border-input bg-card px-3 py-2 text-sm"
                />
                {errors.message && (
                  <p id="contact-message-error" className="text-sm text-destructive">
                    {errors.message}
                  </p>
                )}
              </div>
              <div className="sm:col-span-2">
                <Button type="submit" className="h-11 px-6" disabled={submitting}>
                  {submitting ? "Sending…" : "Send message"}
                </Button>
              </div>
            </form>
          )}
        </div>
      </div>
      <aside className="space-y-3 text-sm">
        <h2 className="text-lg font-bold text-forest">Other ways to reach us</h2>
        {site.isError ? (
          <ErrorState title="Contact details didn't load" onRetry={() => site.refetch()} />
        ) : (
          <dl className="space-y-2">
            {site.data?.support_email && (
              <div>
                <dt className="text-muted-foreground">Email</dt>
                <dd>
                  <a
                    className="font-medium text-forest underline"
                    href={`mailto:${site.data.support_email}`}
                  >
                    {site.data.support_email}
                  </a>
                </dd>
              </div>
            )}
            {site.data?.support_phone && (
              <div>
                <dt className="text-muted-foreground">Phone</dt>
                <dd>
                  <a
                    className="font-medium text-forest underline"
                    href={`tel:${site.data.support_phone}`}
                  >
                    {site.data.support_phone}
                  </a>
                </dd>
              </div>
            )}
          </dl>
        )}
      </aside>
    </div>
  )
}
