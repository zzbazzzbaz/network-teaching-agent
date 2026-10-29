import { Toaster as SonnerToaster } from "sonner"

function Toaster() {
  return (
    <SonnerToaster
      position="bottom-right"
      gap={8}
      toastOptions={{
        className:
          "!rounded-lg !border !border-line !bg-surface !text-ink !shadow-[0_10px_38px_rgba(18,26,28,0.14)] !text-[13px]",
        descriptionClassName: "!text-ink-muted",
      }}
    />
  )
}

export { Toaster }
