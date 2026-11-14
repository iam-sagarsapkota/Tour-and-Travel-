import { cn } from "@/lib/utils"
import type { Difficulty } from "@/types/api"

const STYLES: Record<Difficulty, { label: string; className: string }> = {
  easy: { label: "Easy", className: "bg-emerald-100 text-emerald-900" },
  moderate: { label: "Moderate", className: "bg-amber-100 text-amber-900" },
  difficult: { label: "Difficult", className: "bg-orange-100 text-orange-900" },
  extreme: { label: "Extreme", className: "bg-red-100 text-red-900" },
}

/** Difficulty is always shown as text, never by colour alone. */
export function DifficultyBadge({
  difficulty,
  className,
}: {
  difficulty: Difficulty
  className?: string
}) {
  const style = STYLES[difficulty]
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
        style.className,
        className,
      )}
    >
      <span className="sr-only">Difficulty: </span>
      {style.label}
    </span>
  )
}
