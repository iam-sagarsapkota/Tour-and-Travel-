import { lazy, Suspense } from "react"

// GSAP-based React Bits component, loaded in its own chunk.
const SplitText = lazy(() => import("./reactbits/SplitText"))

/**
 * Homepage hero headline (React Bits "Split Text").
 *
 * The plain <h1> is the Suspense fallback, so the headline is readable at once
 * and keeps its size when the animated version takes over. React Bits skips the
 * animation under prefers-reduced-motion.
 */
export function HeroHeadline({ text, className }: { text: string; className?: string }) {
  return (
    <Suspense fallback={<h1 className={className}>{text}</h1>}>
      <SplitText
        tag="h1"
        text={text}
        className={className}
        splitType="words"
        trigger="load"
        effect="rise"
        delay={60}
        duration={0.8}
        textAlign="center"
      />
    </Suspense>
  )
}
