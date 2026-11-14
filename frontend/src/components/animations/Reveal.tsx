import { lazy, Suspense } from "react"
import type { ReactNode } from "react"

// GSAP-based React Bits component, loaded in its own chunk.
const AnimatedContent = lazy(() => import("./reactbits/AnimatedContent"))

/**
 * Scroll reveal for editorial sections (React Bits "Animated Content").
 *
 * Shared settings live here so pages never configure motion themselves.
 * Content renders immediately as the Suspense fallback, so there is no layout
 * shift while the animation chunk loads; the React Bits component itself
 * skips the animation when the user prefers reduced motion.
 */
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode
  delay?: number
  className?: string
}) {
  return (
    <Suspense fallback={<div className={className}>{children}</div>}>
      <AnimatedContent distance={32} duration={0.6} delay={delay} className={className}>
        {children}
      </AnimatedContent>
    </Suspense>
  )
}
