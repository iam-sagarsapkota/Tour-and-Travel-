import { MountainIcon } from "lucide-react"

import { cn } from "@/lib/utils"

/**
 * Cover photo with a fixed aspect ratio (no layout shift) and a branded
 * placeholder when the record has no image yet.
 */
export function CoverImage({
  src,
  alt,
  className,
  eager = false,
}: {
  src: string | null
  alt: string
  className?: string
  eager?: boolean
}) {
  if (!src) {
    return (
      <div
        role="img"
        aria-label={alt}
        className={cn(
          "flex items-center justify-center bg-gradient-to-br from-forest to-forest-light",
          className,
        )}
      >
        <MountainIcon className="size-12 text-gold/80" aria-hidden="true" />
      </div>
    )
  }
  return (
    <img
      src={src}
      alt={alt}
      loading={eager ? "eager" : "lazy"}
      decoding="async"
      className={cn("object-cover", className)}
    />
  )
}
