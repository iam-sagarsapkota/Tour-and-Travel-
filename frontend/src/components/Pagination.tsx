import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react"

import { Button } from "@/components/ui/button"

export function Pagination({
  page,
  pageCount,
  onChange,
}: {
  page: number
  pageCount: number
  onChange: (page: number) => void
}) {
  if (pageCount <= 1) return null
  return (
    <nav aria-label="Pagination" className="flex items-center justify-center gap-4">
      <Button
        variant="outline"
        className="h-10 px-3"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        <ChevronLeftIcon aria-hidden="true" />
        Previous
      </Button>
      <p className="text-sm text-muted-foreground" aria-live="polite">
        Page {page} of {pageCount}
      </p>
      <Button
        variant="outline"
        className="h-10 px-3"
        disabled={page >= pageCount}
        onClick={() => onChange(page + 1)}
      >
        Next
        <ChevronRightIcon aria-hidden="true" />
      </Button>
    </nav>
  )
}
