import React from 'react';
import { useLocation } from 'react-router-dom';
import { Zap, Activity, Leaf } from 'lucide-react';

export default function Footer() {
  const location = useLocation();

  if (location.pathname === '/login') {
    return null;
  }

  return (
    <footer className="border-t border-slate-200 bg-white text-slate-500 py-6 text-xs font-mono">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center space-x-2">
          <Zap className="w-4 h-4 text-teal-600" />
          <span className="text-slate-800 font-sans font-semibold text-xs">
            RESK ENERGY INTELLIGENCE PLATFORM
          </span>
          <span className="text-slate-300">//</span>
          <span className="text-slate-500 text-[11px]">Industrial Optimization & Demand Management</span>
        </div>
        <div className="flex items-center space-x-5 text-[11px]">
          <span className="flex items-center space-x-1.5 text-slate-600">
            <Activity className="w-3.5 h-3.5 text-teal-600" />
            <span>GRID SYNCHRONIZED</span>
          </span>
          <span className="flex items-center space-x-1.5 text-emerald-700 font-medium">
            <Leaf className="w-3.5 h-3.5 text-emerald-600" />
            <span>ISO 50001 READY</span>
          </span>
          <span className="text-slate-400">v1.2.0</span>
        </div>
      </div>
    </footer>
  );
}
