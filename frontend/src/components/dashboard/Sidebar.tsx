import { BarChart3, Bolt, Bot, Factory, FlaskConical, Gauge, Settings2, ShieldAlert, Wrench } from 'lucide-react'

const items = [
  ['Overview', Gauge], ['Energy Dashboard', BarChart3], ['Production Optimizer', Settings2], ['Anomaly Detection', ShieldAlert], ['What-if Simulator', FlaskConical], ['Savings & ROI', Bolt], ['Carbon Dashboard', Factory], ['Maintenance', Wrench],
]

export function Sidebar({active, setActive}:{active:string; setActive:(s:string)=>void}) {
  return <aside className="hidden w-[250px] shrink-0 flex-col border-r border-white/[.06] bg-[#08120e] lg:flex">
    <div className="flex h-20 items-center gap-3 border-b border-white/[.06] px-6">
      <div className="grid h-9 w-9 place-items-center rounded-xl bg-acid text-ink"><Bot size={20}/></div>
      <div><div className="font-display text-sm font-bold tracking-wide">FACTORY</div><div className="text-[10px] font-semibold uppercase tracking-[.22em] text-white/35">Energy OS</div></div>
    </div>
    <div className="flex-1 px-3 py-5">
      <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-[.2em] text-white/25">Operations</div>
      <nav className="space-y-1">
        {items.map(([label, Icon]) => <button key={label as string} onClick={()=>setActive(label as string)} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition ${active===label?'bg-white/[.06] text-white':'text-white/45 hover:bg-white/[.035] hover:text-white'}`}><Icon size={17}/><span>{label as string}</span>{label==='Anomaly Detection' && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-acid shadow-[0_0_12px_#d7ff57]"/>}</button>)}
      </nav>
    </div>
    <div className="border-t border-white/[.06] p-4">
      <div className="rounded-xl border border-white/[.06] bg-white/[.025] p-3">
        <div className="mb-2 flex items-center gap-2"><div className="h-2 w-2 rounded-full bg-mint shadow-[0_0_10px_#73f0b6]"/><span className="text-xs font-semibold">Plant gateway online</span></div>
        <div className="flex items-center justify-between text-[11px] text-white/35"><span>Uptime</span><span>99.94%</span></div>
      </div>
    </div>
  </aside>
}
