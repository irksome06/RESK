import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import { Card } from '../ui/Card'

export function MetricCard({label,value,unit,delta,positive=true}:{label:string;value:string|number;unit?:string;delta?:string;positive?:boolean}){
 const Icon = delta ? (positive ? ArrowDownRight : ArrowUpRight) : Minus
 return <Card className="p-4"><div className="text-[11px] font-semibold uppercase tracking-[.14em] text-white/35">{label}</div><div className="mt-3 flex items-end gap-1.5"><div className="font-display text-2xl font-semibold tracking-tight">{value}</div>{unit && <div className="pb-1 text-xs text-white/30">{unit}</div>}</div>{delta && <div className={`mt-2 flex items-center gap-1 text-xs ${positive?'text-mint':'text-amber-200'}`}><Icon size={13}/>{delta}<span className="text-white/25">vs baseline</span></div>}</Card>
}
