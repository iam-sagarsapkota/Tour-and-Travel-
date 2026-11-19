import { CheckCircle2Icon, MailWarningIcon } from "lucide-react"
import { useState } from "react"
import type { FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"

import { Field, FormError } from "@/components/forms"
import type { Errors } from "@/components/forms"
import { Button } from "@/components/ui/button"
import {
  useChangePassword,
  useResendVerification,
  useSessions,
  useSignOutEverywhere,
  useUpdateProfile,
} from "@/features/account/queries"
import { useAuth } from "@/features/auth/AuthContext"
import { ApiError } from "@/lib/api"
import { tokenStore } from "@/lib/tokens"
import type { User } from "@/types/api"

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border bg-card p-5 sm:p-6">
      <h2 className="text-lg font-bold text-forest">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  )
}

function fieldErrors(error: unknown, names: string[]): Errors {
  if (!(error instanceof ApiError)) return error ? { form: "Something went wrong." } : {}
  const errors: Errors = { form: error.formError }
  for (const name of names) errors[name] = error.first(name)
  if (!Object.values(errors).some(Boolean)) errors.form = error.message
  return errors
}

function ProfileForm({ user }: { user: User }) {
  const { refreshUser } = useAuth()
  const update = useUpdateProfile()
  const [errors, setErrors] = useState<Errors>({})

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const value = (name: string) => String(data.get(name) ?? "").trim()
    if (!value("full_name")) {
      setErrors({ full_name: "Enter your full name." })
      return
    }
    setErrors({})
    try {
      await update.mutateAsync({
        full_name: value("full_name"),
        profile: {
          nationality: value("nationality"),
          emergency_contact_name: value("emergency_contact_name"),
          emergency_contact_phone: value("emergency_contact_phone"),
          trip_reminders: data.get("trip_reminders") === "on",
        },
      })
      await refreshUser()
      toast.success("Profile saved")
    } catch (error) {
      setErrors(fieldErrors(error, ["full_name"]))
    }
  }

  return (
    <form onSubmit={submit} noValidate className="grid gap-4 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <FormError message={errors.form} />
      </div>
      <Field
        label="Full name"
        name="full_name"
        defaultValue={user.full_name}
        error={errors.full_name}
      />
      <Field label="Nationality" name="nationality" defaultValue={user.profile.nationality} />
      <Field
        label="Emergency contact name"
        name="emergency_contact_name"
        defaultValue={user.profile.emergency_contact_name}
      />
      <Field
        label="Emergency contact phone"
        name="emergency_contact_phone"
        type="tel"
        defaultValue={user.profile.emergency_contact_phone}
      />
      <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm sm:col-span-2">
        <input
          type="checkbox"
          name="trip_reminders"
          defaultChecked={user.profile.trip_reminders}
          className="size-5 accent-forest"
        />
        Email me a reminder a few days before each trip
      </label>
      <div className="sm:col-span-2">
        <Button type="submit" className="h-11 px-5" disabled={update.isPending}>
          {update.isPending ? "Saving…" : "Save profile"}
        </Button>
      </div>
    </form>
  )
}

function ContactDetails({ user }: { user: User }) {
  const resend = useResendVerification()
  return (
    <dl className="space-y-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <dt className="text-muted-foreground">Email</dt>
        <dd className="flex flex-wrap items-center gap-2 font-medium">
          {user.email ?? "Not set"}
          {user.email &&
            (user.email_verified ? (
              <span className="inline-flex items-center gap-1 text-success">
                <CheckCircle2Icon className="size-4" aria-hidden="true" /> Verified
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-warning">
                <MailWarningIcon className="size-4" aria-hidden="true" /> Not verified
              </span>
            ))}
        </dd>
      </div>
      {user.email && !user.email_verified && (
        <div className="rounded-lg bg-amber-50 p-3 text-amber-950">
          {resend.isSuccess ? (
            <p role="status">We've sent a new link. Check your inbox.</p>
          ) : (
            <>
              <p>Confirm your email so we can reach you about your trips.</p>
              <Button
                variant="outline"
                className="mt-2 h-10 px-4"
                disabled={resend.isPending}
                onClick={() => resend.mutate()}
              >
                {resend.isPending ? "Sending…" : "Send verification link"}
              </Button>
              {resend.isError && (
                <p role="alert" className="mt-2 text-destructive">
                  {resend.error instanceof ApiError ? resend.error.message : "Could not send."}
                </p>
              )}
            </>
          )}
        </div>
      )}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <dt className="text-muted-foreground">Phone</dt>
        <dd className="font-medium">{user.phone ?? "Not set"}</dd>
      </div>
      <p className="text-xs text-muted-foreground">
        To change your email or phone number, contact us; we verify changes to keep your account
        safe.
      </p>
    </dl>
  )
}

function PasswordForm() {
  const change = useChangePassword()
  const [errors, setErrors] = useState<Errors>({})

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    const input = {
      current_password: String(data.get("current_password") ?? ""),
      new_password: String(data.get("new_password") ?? ""),
      new_password_confirm: String(data.get("new_password_confirm") ?? ""),
    }
    const local: Errors = {}
    if (!input.current_password) local.current_password = "Enter your current password."
    if (input.new_password.length < 8) local.new_password = "Use at least 8 characters."
    if (input.new_password !== input.new_password_confirm)
      local.new_password_confirm = "Passwords do not match."
    setErrors(local)
    if (Object.keys(local).length) return
    try {
      const result = await change.mutateAsync(input)
      tokenStore.set(result.tokens) // every other session was signed out by the server
      form.reset()
      toast.success("Password changed. Other devices have been signed out.")
    } catch (error) {
      setErrors(fieldErrors(error, ["current_password", "new_password", "new_password_confirm"]))
    }
  }

  return (
    <form onSubmit={submit} noValidate className="max-w-md space-y-4">
      <FormError message={errors.form} />
      <Field
        label="Current password"
        name="current_password"
        type="password"
        autoComplete="current-password"
        error={errors.current_password}
      />
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
      <Button type="submit" className="h-11 px-5" disabled={change.isPending}>
        {change.isPending ? "Changing…" : "Change password"}
      </Button>
    </form>
  )
}

function Sessions() {
  const sessions = useSessions()
  const signOut = useSignOutEverywhere()
  const { endSession } = useAuth()
  const navigate = useNavigate()
  const [confirming, setConfirming] = useState(false)
  const count = sessions.data?.length ?? 0

  return (
    <div className="space-y-3 text-sm">
      <p>
        {sessions.isPending
          ? "Checking signed-in devices…"
          : `You're signed in on ${count} ${count === 1 ? "browser or device" : "browsers or devices"}.`}
      </p>
      {confirming ? (
        <div role="group" aria-labelledby="signout-q" className="rounded-xl border p-4">
          <p id="signout-q" className="font-semibold">
            Sign out everywhere, including this browser?
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              variant="destructive"
              className="h-10 px-4"
              disabled={signOut.isPending}
              onClick={() =>
                signOut.mutate(undefined, {
                  onSuccess: () => {
                    endSession()
                    navigate("/login", { replace: true })
                  },
                })
              }
            >
              {signOut.isPending ? "Signing out…" : "Yes, sign out everywhere"}
            </Button>
            <Button variant="outline" className="h-10 px-4" onClick={() => setConfirming(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <Button variant="outline" className="h-10 px-4" onClick={() => setConfirming(true)}>
          Sign out of all devices
        </Button>
      )}
    </div>
  )
}

export default function ProfilePage() {
  const { user } = useAuth()
  if (!user) return null
  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-10">
      <h1 className="text-3xl font-extrabold text-forest">Profile & security</h1>
      <Section title="Your details">
        <ProfileForm user={user} />
      </Section>
      <Section title="Contact details">
        <ContactDetails user={user} />
      </Section>
      <Section title="Password">
        <PasswordForm />
      </Section>
      <Section title="Signed-in devices">
        <Sessions />
      </Section>
    </div>
  )
}
