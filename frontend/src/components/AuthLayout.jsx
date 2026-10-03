import React from 'react';
import { Zap, TrendingDown, Activity, Leaf, Factory } from 'lucide-react';

export default function AuthLayout({ children }) {
  return (
    <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center py-10 px-4 sm:px-6 lg:px-8 bg-light-energy-grid relative">
      <div className="w-full max-w-6xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-14 items-center">
          
          {/* LEFT COLUMN: RESK Branding & Value Proposition */}
          <div className="lg:col-span-5 space-y-6 text-left">
            {/* Platform pill badge */}
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-mono font-medium shadow-2xs">
              <Zap className="w-3.5 h-3.5 text-teal-600" />
              <span className="font-semibold tracking-wider uppercase">Energy Intelligence Platform</span>
            </div>

            {/* Brand Header */}
            <div>
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-900" style={{ fontFamily: 'var(--font-display, sans-serif)' }}>
                RESK
              </h1>
              <p className="text-xl sm:text-2xl font-bold mt-2 tracking-wide flex items-center gap-2">
                <span className="text-teal-700">Monitor</span>
                <span className="text-slate-300">•</span>
                <span className="text-amber-600">Optimize</span>
                <span className="text-slate-300">•</span>
                <span className="text-emerald-600">Reduce</span>
              </p>
            </div>

            <p className="text-sm text-slate-600 leading-relaxed font-normal">
              Industrial-grade energy intelligence for high-consumption manufacturing plants, power grids, and enterprise facilities. Continuous telemetry, demand forecasting, and automated peak-shaving.
            </p>

            {/* Visual Mini Data Card: Energy Flow & Peak Shaving */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200/90 shadow-md shadow-slate-200/40 space-y-3.5">
              <div className="flex items-center justify-between text-xs border-b border-slate-100 pb-2.5">
                <div className="flex items-center space-x-2 text-slate-700 font-mono text-[11px] font-medium">
                  <Activity className="w-3.5 h-3.5 text-teal-600" />
                  <span>GRID DEMAND TELEMETRY</span>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold">
                  -24.8% PEAK LOAD
                </span>
              </div>

              {/* Data Visualization graphic on clean light canvas */}
              <div className="h-16 w-full relative flex items-end">
                <svg className="w-full h-full overflow-visible" viewBox="0 0 280 60" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="chartGreenLight" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10B981" stopOpacity="0.22" />
                      <stop offset="100%" stopColor="#10B981" stopOpacity="0.01" />
                    </linearGradient>
                  </defs>
                  {/* Subtle baseline grid lines */}
                  <line x1="0" y1="15" x2="280" y2="15" stroke="rgba(15, 23, 42, 0.07)" strokeDasharray="3 3" />
                  <line x1="0" y1="40" x2="280" y2="40" stroke="rgba(15, 23, 42, 0.07)" strokeDasharray="3 3" />
                  
                  {/* Unoptimized Peak Load Curve (Dotted Amber Line) */}
                  <path
                    d="M0,45 Q50,42 90,20 T170,10 T230,30 T280,38"
                    fill="none"
                    stroke="#D97706"
                    strokeWidth="1.75"
                    strokeDasharray="3 2"
                    opacity="0.75"
                  />
                  
                  {/* Optimized Load with RESK (Emerald Solid Line & Soft Gradient Fill) */}
                  <path
                    d="M0,48 Q50,44 90,32 T170,26 T230,28 T280,32"
                    fill="none"
                    stroke="#059669"
                    strokeWidth="2.25"
                  />
                  <path
                    d="M0,48 Q50,44 90,32 T170,26 T230,28 T280,32 L280,60 L0,60 Z"
                    fill="url(#chartGreenLight)"
                  />
                </svg>
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-1">
                <span className="flex items-center gap-1.5 text-amber-700">
                  <span className="w-2.5 h-0.5 bg-amber-500 inline-block rounded-full"></span>
                  <span>Unmanaged Peak</span>
                </span>
                <span className="flex items-center gap-1.5 text-emerald-700 font-semibold">
                  <span className="w-2.5 h-0.5 bg-emerald-600 inline-block rounded-full"></span>
                  <span>RESK Optimized</span>
                </span>
              </div>
            </div>

            {/* Core Value Pillars */}
            <div className="space-y-3 pt-1">
              <div className="flex items-start space-x-3 text-xs">
                <div className="p-1 rounded-md bg-teal-50 text-teal-700 mt-0.5 border border-teal-200">
                  <Zap className="w-3.5 h-3.5" />
                </div>
                <div>
                  <span className="font-semibold text-slate-900">Sub-second Grid Telemetry:</span>{' '}
                  <span className="text-slate-600">Connect smart meters, PLCs, and SCADA infrastructure.</span>
                </div>
              </div>

              <div className="flex items-start space-x-3 text-xs">
                <div className="p-1 rounded-md bg-amber-50 text-amber-700 mt-0.5 border border-amber-200">
                  <TrendingDown className="w-3.5 h-3.5" />
                </div>
                <div>
                  <span className="font-semibold text-slate-900">Automated Peak Shaving:</span>{' '}
                  <span className="text-slate-600">Mitigate steep grid demand charges before thresholds trigger.</span>
                </div>
              </div>

              <div className="flex items-start space-x-3 text-xs">
                <div className="p-1 rounded-md bg-emerald-50 text-emerald-700 mt-0.5 border border-emerald-200">
                  <Leaf className="w-3.5 h-3.5" />
                </div>
                <div>
                  <span className="font-semibold text-slate-900">ISO 50001 Energy Accounting:</span>{' '}
                  <span className="text-slate-600">Automated compliance, carbon tracking, and tariff optimization.</span>
                </div>
              </div>
            </div>

            {/* Trust badge */}
            <div className="pt-2 flex items-center space-x-2 text-xs text-slate-500">
              <Factory className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span>Deployed across manufacturing, refining, and industrial plants worldwide.</span>
            </div>
          </div>

          {/* RIGHT COLUMN: The Authentication Form */}
          <div className="lg:col-span-7 flex justify-center">
            <div className="w-full max-w-xl">
              {children}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
