import { MinusIcon, PlusIcon } from "lucide-react"
import { useId, useState } from "react"
import type { FormEvent } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

import type { CreateBookingInput, ParticipantInput } from "./queries"

interface Props {
  departureId: string
  minParticipants: number
  maxParticipants: number
  leadName: string
  cancellationPolicy: string
  submitting: boolean
  /** Error from the server, shown above the submit button. */
  serverError?: string
  fieldErrors?: Record<string, string | undefined>
  onCountChange: (count: number) => void
  onSubmit: (input: CreateBookingInput) => void
}

/**
 * Party size, traveller names and policy acknowledgement. Deliberately free of
 * animation (PRD 10.1). The price is shown separately from the server quote.
 */
export function BookingForm({
  departureId,
  minParticipants,
  maxParticipants,
  leadName,
  cancellationPolicy,
  submitting,
  serverError,
  fieldErrors = {},
  onCountChange,
  onSubmit,
}: Props) {
  const id = useId()
  const [travellers, setTravellers] = useState<ParticipantInput[]>(() =>
    Array.from({ length: minParticipants }, (_, index) => ({
      full_name: index === 0 ? leadName : "",
      nationality: "",
    })),
  )
  const [accepted, setAccepted] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  function setCount(count: number) {
    const next = Math.min(Math.max(count, minParticipants), maxParticipants)
    setTravellers((current) =>
      next > current.length
        ? [
            ...current,
            ...Array.from({ length: next - current.length }, () => ({
              full_name: "",
              nationality: "",
            })),
          ]
        : current.slice(0, next),
    )
    onCountChange(next)
  }

  function update(index: number, field: keyof ParticipantInput, value: string) {
    setTravellers((current) =>
      current.map((person, i) => (i === index ? { ...person, [field]: value } : person)),
    )
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const next: Record<string, string> = {}
    travellers.forEach((person, index) => {
      if (!person.full_name.trim()) next[`name-${index}`] = "Enter this traveller's full name."
    })
    if (!accepted) next.policy = "Please confirm you have read the cancellation policy."
    setErrors(next)
    if (Object.keys(next).length) return
    onSubmit({
      departure: departureId,
      participants: travellers.map((person) => ({
        full_name: person.full_name.trim(),
        nationality: person.nationality?.trim() ?? "",
      })),
      policy_accepted: true,
    })
  }

  const count = travellers.length
  const policyError = errors.policy ?? fieldErrors.policy_accepted

  return (
    <form onSubmit={submit} noValidate className="space-y-8">
      <fieldset>
        <legend className="text-lg font-bold text-forest">How many travellers?</legend>
        <div className="mt-3 flex items-center gap-3">
          <Button
            type="button"
            variant="outline"
            className="size-11"
            onClick={() => setCount(count - 1)}
            disabled={count <= minParticipants}
            aria-label="Remove a traveller"
          >
            <MinusIcon aria-hidden="true" />
          </Button>
          <output
            className="min-w-12 text-center font-heading text-2xl font-bold"
            aria-live="polite"
            aria-label={`${count} traveller${count === 1 ? "" : "s"}`}
          >
            {count}
          </output>
          <Button
            type="button"
            variant="outline"
            className="size-11"
            onClick={() => setCount(count + 1)}
            disabled={count >= maxParticipants}
            aria-label="Add a traveller"
          >
            <PlusIcon aria-hidden="true" />
          </Button>
          <p className="text-sm text-muted-foreground">
            {minParticipants > 1 ? `Groups of ${minParticipants}-` : "Up to "}
            {maxParticipants} per booking
          </p>
        </div>
      </fieldset>

      <fieldset className="space-y-4">
        <legend className="text-lg font-bold text-forest">Traveller details</legend>
        <p className="text-sm text-muted-foreground">
          Names as they appear on passports or ID, needed for permits.
        </p>
        {fieldErrors.participants && (
          <p role="alert" className="text-sm text-destructive">
            {fieldErrors.participants}
          </p>
        )}
        {travellers.map((person, index) => {
          const nameId = `${id}-name-${index}`
          const nameError = errors[`name-${index}`]
          return (
            <div key={index} className="grid gap-3 rounded-xl border bg-card p-4 sm:grid-cols-2">
              <p className="font-semibold sm:col-span-2">
                {index === 0 ? "Lead traveller" : `Traveller ${index + 1}`}
              </p>
              <div className="space-y-1.5">
                <Label htmlFor={nameId}>Full name</Label>
                <Input
                  id={nameId}
                  className="h-11"
                  autoComplete={index === 0 ? "name" : "off"}
                  value={person.full_name}
                  aria-invalid={nameError ? true : undefined}
                  aria-describedby={nameError ? `${nameId}-error` : undefined}
                  onChange={(event) => update(index, "full_name", event.target.value)}
                />
                {nameError && (
                  <p id={`${nameId}-error`} className="text-sm text-destructive">
                    {nameError}
                  </p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor={`${id}-nat-${index}`}>Nationality (optional)</Label>
                <Input
                  id={`${id}-nat-${index}`}
                  className="h-11"
                  value={person.nationality ?? ""}
                  onChange={(event) => update(index, "nationality", event.target.value)}
                />
              </div>
            </div>
          )
        })}
      </fieldset>

      <fieldset className="space-y-3">
        <legend className="text-lg font-bold text-forest">Cancellation policy</legend>
        <p className="whitespace-pre-line rounded-xl bg-secondary/60 p-4 text-sm">
          {cancellationPolicy ||
            "This trip has no published cancellation policy yet. Contact us before booking."}
        </p>
        <label className="flex min-h-11 cursor-pointer items-start gap-3 text-sm">
          <input
            type="checkbox"
            className="mt-0.5 size-5 accent-forest"
            checked={accepted}
            onChange={(event) => setAccepted(event.target.checked)}
            aria-invalid={policyError ? true : undefined}
            aria-describedby={policyError ? `${id}-policy-error` : undefined}
          />
          I have read and accept the booking and cancellation policy.
        </label>
        {policyError && (
          <p id={`${id}-policy-error`} className="text-sm text-destructive">
            {policyError}
          </p>
        )}
      </fieldset>

      {serverError && (
        <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {serverError}
        </p>
      )}
      <Button
        type="submit"
        className="h-12 w-full text-base sm:w-auto sm:px-8"
        disabled={submitting}
      >
        {submitting ? "Reserving your places…" : "Reserve places"}
      </Button>
    </form>
  )
}
