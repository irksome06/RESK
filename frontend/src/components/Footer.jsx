import React from 'react';
import { ShieldCheck, Cpu } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-slate-900 bg-slate-950/70 text-slate-500 py-6 text-xs font-mono">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-amber-500/70" />
          <span>RESK DEFENSE PLATFORM // SECURE ORG PROTOCOL</span>
        </div>
        <div className="flex items-center space-x-6 text-[11px]">
          <span className="flex items-center space-x-1.5">
            <Cpu className="w-3.5 h-3.5 text-slate-400" />
            <span>ENCRYPTED_SHA256</span>
          </span>
          <span>ZERO_TRUST_IDENTITY</span>
          <span className="text-slate-600">v1.0.0</span>
        </div>
      </div>
    </footer>
  );
}
