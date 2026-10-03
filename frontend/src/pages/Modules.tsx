import { Card } from '../components/ui/Card'
import { BarChart3, Bolt, Factory, ShieldAlert, Settings2, Wrench } from 'lucide-react'

const modules = [
 {name:'Energy Dashboard',icon:BarChart3,desc:'Load, tariff, generation, intensity and plant energy KPIs.',status:'Live'},
 {name:'Production Optimizer',icon:Settings2,desc:'Constraint-aware production scheduling through OR-Tools.',status:'Live'},
 {name:'Anomaly Detection',icon:ShieldAlert,desc:'Detect deviations from operating baselines using machine learning.',status:'Live'},
 {name:'Savings & ROI',icon:Bolt,desc:'Translate technical changes into cost, payback and ROI outcomes.',status:'Live'},
 {name:'Carbon Dashboard',icon:Factory,desc:'Track energy-linked carbon emissions and reduction opportunities.',status:'Ready'},
 {name:'Maintenance',icon:Wrench,desc:'Align maintenance windows with production slack and tariff periods.',status:'Live'},
]
export default function Modules(){return <div className="grid-bg grid gap-4 pb-10 sm:grid-cols-2 xl:grid-cols-3">{modules.map(({name,icon:Icon,desc,status})=><Card key={name} className="group p-5 transition hover:-translate-y-0.5 hover:border-acid/15"><div className="flex items-start justify-between"><div className="rounded-xl bg-white/[.035] p-3 text-acid"><Icon size={18}/></div><span className="text-[10px] uppercase tracking-[.2em] text-mint/70">{status}</span></div><h3 className="mt-8 font-display text-base font-semibold">{name}</h3><p className="mt-2 text-xs leading-5 text-white/35">{desc}</p><div className="mt-6 h-px bg-white/[.05]"/><div className="mt-4 text-[10px] uppercase tracking-[.16em] text-white/20">Integrated with REST API</div></Card>)}</div>}
