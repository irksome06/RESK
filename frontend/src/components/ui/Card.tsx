import type { ReactNode } from 'react'
export function Card({children, className=''}:{children:ReactNode; className?:string}) { return <section className={`glass rounded-2xl shadow-glow ${className}`}>{children}</section> }
