import { useState } from 'react'
import { Sidebar } from './components/dashboard/Sidebar'
import { Topbar } from './components/dashboard/Topbar'
import Dashboard from './pages/Dashboard'
import Simulator from './pages/Simulator'
import Modules from './pages/Modules'

export default function App(){
 const [active,setActive]=useState('Overview')
 const content = active==='Overview' ? <Dashboard/> : active==='What-if Simulator' ? <Simulator/> : <Modules/>
 return <div className="flex min-h-screen bg-ink text-white"><Sidebar active={active} setActive={setActive}/><main className="min-w-0 flex-1"><Topbar/><div className="px-4 pt-5 lg:px-8">{content}</div></main></div>
}
