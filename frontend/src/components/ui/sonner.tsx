import { Toaster as Sonner, type ToasterProps } from "sonner"

/** App-wide toast outlet. Light theme only, so no theme provider is needed. */
const Toaster = (props: ToasterProps) => (
  <Sonner
    theme="light"
    position="top-center"
    toastOptions={{
      classNames: {
        toast: "!bg-card !text-card-foreground !border-border !shadow-md",
        success: "!text-success",
        error: "!text-destructive",
      },
    }}
    {...props}
  />
)

export { Toaster }
