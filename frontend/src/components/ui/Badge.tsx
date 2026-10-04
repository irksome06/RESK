import type { ReactNode } from 'react'
export function Badge({children, tone='default'}:{children:ReactNode; tone?:'default'|'good'|'warn'|'bad'}) {
  const cls = {default:'border-white/10 text-white/65 bg-white/[.03]',good:'border-mint/20 text-mint bg-mint/[.07]',warn:'border-amber-300/20 text-amber-200 bg-amber-300/[.07]',bad:'border-red-300/20 text-red-200 bg-red-300/[.07]'}[tone]
  return <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold tracking-wide ${cls}`}>{children}</span>
}
