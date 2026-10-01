import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shield,
  Building2,
  Mail,
  Briefcase,
  MapPin,
  Calendar,
  CheckCircle2,
  Copy,
  Check,
  LogOut,
  KeyRound,
  Terminal,
  Activity,
  Layers,
  Server,
  Lock,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function DashboardPage() {
  const { organization, logout } = useAuth();
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);

  const handleCopyId = () => {
    if (organization?.registration_id) {
      navigator.clipboard.writeText(organization.registration_id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A';
    try {
      return new Date(isoString).toLocaleString('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="min-h-[85vh] py-8 px-4 sm:px-6 lg:px-8 bg-industrial-grid">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Top Operational Status Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-slate-900/90 border border-slate-800 rounded-xl shadow-xl backdrop-blur-xl relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-500 via-amber-400 to-amber-600"></div>

          <div className="flex items-center space-x-4">
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
              <Shield className="w-8 h-8" />
            </div>
            <div>
              <div className="flex items-center space-x-3">
                <h1 className="text-xl sm:text-2xl font-bold text-white tracking-wide">
                  {organization?.organization_name || 'Organization Dashboard'}
                </h1>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-950/60 text-emerald-400 border border-emerald-500/40 flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span>CLEARED // LEVEL 4</span>
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-1">
                Facility Operational Control & Security Identity Nexus
              </p>
            </div>
          </div>

          {/* Quick Registration ID display */}
          <div className="flex items-center space-x-3 bg-slate-950/80 px-4 py-2.5 rounded-lg border border-slate-800">
            <div>
              <span className="block text-[10px] font-mono text-slate-500 uppercase">Registration ID</span>
              <span className="font-mono text-base font-bold text-amber-400 tracking-wider">
                {organization?.registration_id}
              </span>
            </div>
            <button
              onClick={handleCopyId}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
              title="Copy Registration ID"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* 3-Column Metrics / Core Panels */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Panel 1: Entity Profile */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center space-x-2 text-xs font-mono text-slate-300 font-bold uppercase tracking-wider">
                <Building2 className="w-4 h-4 text-amber-400" />
                <span>Entity Credentials</span>
              </div>
              <span className="text-[10px] font-mono text-slate-500">ID: {organization?.organization_id?.slice(0, 8)}...</span>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="block text-slate-400 text-[11px]">Legal Entity</span>
                <span className="font-medium text-slate-200 text-sm">{organization?.organization_name}</span>
              </div>

              <div>
                <span className="block text-slate-400 text-[11px]">Primary Dispatch Email</span>
                <div className="flex items-center space-x-1.5 mt-0.5">
                  <span className="font-mono text-slate-300">{organization?.official_email}</span>
                  {organization?.email_verified && (
                    <span className="inline-flex items-center space-x-0.5 px-1.5 py-0.2 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      <CheckCircle2 className="w-3 h-3 mr-0.5" />
                      VERIFIED
                    </span>
                  )}
                </div>
              </div>

              <div>
                <span className="block text-slate-400 text-[11px]">Industry Classification</span>
                <span className="text-slate-300">{organization?.industry}</span>
              </div>

              <div>
                <span className="block text-slate-400 text-[11px]">Operational Headquarters</span>
                <span className="text-slate-300">{organization?.location}</span>
              </div>

              <div>
                <span className="block text-slate-400 text-[11px]">Enrollment Timestamp</span>
                <span className="font-mono text-slate-400 text-[11px]">{formatDate(organization?.created_at)}</span>
              </div>
            </div>
          </div>

          {/* Panel 2: Zero Trust Identity & Security */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center space-x-2 text-xs font-mono text-slate-300 font-bold uppercase tracking-wider">
                <Lock className="w-4 h-4 text-emerald-400" />
                <span>Identity Protocol</span>
              </div>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
                ACTIVE
              </span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
                <span className="block text-[11px] font-mono text-slate-400 mb-1">
                  NORMAL LOGIN IDENTIFIER:
                </span>
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-amber-400 text-sm tracking-wider">
                    {organization?.registration_id}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">NON-EMAIL AUTH</span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between text-slate-300 py-1 border-b border-slate-800/50">
                  <span>Password Hash Algorithm</span>
                  <span className="font-mono text-slate-400">BCRYPT-BLOWFISH-12</span>
                </div>
                <div className="flex items-center justify-between text-slate-300 py-1 border-b border-slate-800/50">
                  <span>Session Token Type</span>
                  <span className="font-mono text-slate-400">JWT / HS256</span>
                </div>
                <div className="flex items-center justify-between text-slate-300 py-1 border-b border-slate-800/50">
                  <span>Token Expiration</span>
                  <span className="font-mono text-slate-400">24 Hours (Rolling)</span>
                </div>
                <div className="flex items-center justify-between text-slate-300 py-1">
                  <span>Email Verification State</span>
                  <span className="font-mono text-emerald-400">COMPLETED</span>
                </div>
              </div>
            </div>
          </div>

          {/* Panel 3: Quick Operations */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-4">
                <div className="flex items-center space-x-2 text-xs font-mono text-slate-300 font-bold uppercase tracking-wider">
                  <Activity className="w-4 h-4 text-sky-400" />
                  <span>Control Actions</span>
                </div>
                <span className="text-[10px] font-mono text-slate-500">SESSION_ACTIVE</span>
              </div>

              <div className="space-y-2.5">
                <button
                  onClick={handleCopyId}
                  className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg bg-slate-950 hover:bg-slate-800/80 border border-slate-800 text-slate-300 text-xs font-mono transition-colors"
                >
                  <span className="flex items-center space-x-2">
                    <Copy className="w-3.5 h-3.5 text-amber-400" />
                    <span>Copy Registration ID</span>
                  </span>
                  <span className="text-amber-400">{organization?.registration_id}</span>
                </button>

                <div className="p-3 bg-slate-950/70 border border-slate-800/70 rounded-lg text-slate-400 text-[11px] leading-relaxed">
                  <p className="font-semibold text-slate-300 mb-1">Session Management:</p>
                  To switch facilities or sign out, click the Disconnect button below to revoke current bearer authorization.
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-800">
              <button
                onClick={handleLogout}
                className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-lg bg-red-950/40 hover:bg-red-900/60 border border-red-900/60 text-red-200 text-xs font-mono font-bold tracking-wider transition-colors cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
                <span>TERMINATE ACTIVE SESSION</span>
              </button>
            </div>
          </div>
        </div>

        {/* Industrial Telemetry / Activity Log Terminal */}
        <div className="bg-slate-950 border border-slate-800/90 rounded-xl p-5 shadow-2xl font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
            <div className="flex items-center space-x-2 text-slate-400">
              <Terminal className="w-4 h-4 text-amber-500" />
              <span className="font-bold text-slate-300 uppercase tracking-widest text-[11px]">
                RESK System Identity Audit Log
              </span>
            </div>
            <div className="flex items-center space-x-2 text-[10px] text-slate-500">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>LIVE_STREAM</span>
            </div>
          </div>

          <div className="space-y-1.5 text-slate-400 text-[11px]">
            <p className="text-slate-500">[2026-10-01 12:00:00 UTC] IDENTITY_CORE: Daemon initialized on port 8000.</p>
            <p className="text-slate-500">[2026-10-01 12:00:01 UTC] SEC_AUTH: Zero-trust token service verification ready.</p>
            <p className="text-emerald-400/90">
              [{new Date().toISOString()}] AUTH_SESSION: Organization {organization?.registration_id} ({organization?.organization_name}) session active.
            </p>
            <p className="text-amber-400/80">
              [{new Date().toISOString()}] ACCESS_CLEARANCE: Endpoint /auth/me queried with valid Bearer token.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
