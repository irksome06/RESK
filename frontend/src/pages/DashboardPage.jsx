import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Zap,
  Building2,
  CheckCircle2,
  Copy,
  Check,
  LogOut,
  Terminal,
  Activity,
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
    <div className="min-h-[85vh] py-8 px-4 sm:px-6 lg:px-8 bg-light-energy-grid">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Top Operational Status Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-white rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-teal-600 via-amber-400 to-emerald-500"></div>

          <div className="flex items-center space-x-4">
            <div className="p-3.5 rounded-xl bg-teal-50 border border-teal-200 text-teal-600">
              <Zap className="w-8 h-8" />
            </div>
            <div>
              <div className="flex items-center space-x-3">
                <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-wide">
                  {organization?.organization_name || 'Energy Intelligence Workspace'}
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono uppercase bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center space-x-1 font-semibold">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  <span>GRID SYNC // OPTIMAL</span>
                </span>
              </div>
              <p className="text-xs text-slate-500 font-mono mt-1">
                Industrial Energy Optimization & Telemetry Nexus
              </p>
            </div>
          </div>

          {/* Quick Registration ID display */}
          <div className="flex items-center space-x-3 bg-slate-50 px-4 py-2.5 rounded-xl border border-slate-200">
            <div>
              <span className="block text-[10px] font-mono text-slate-500 uppercase">Registration ID</span>
              <span className="font-mono text-base font-bold text-slate-900 tracking-wider">
                {organization?.registration_id}
              </span>
            </div>
            <button
              onClick={handleCopyId}
              className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-500 hover:text-slate-900 transition-colors cursor-pointer"
              title="Copy Registration ID"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* 3-Column Metrics / Core Panels */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Panel 1: Entity Profile */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2 text-xs font-mono text-slate-800 font-bold uppercase tracking-wider">
                <Building2 className="w-4 h-4 text-teal-600" />
                <span>Facility Entity Profile</span>
              </div>
              <span className="text-[10px] font-mono text-slate-400">ID: {organization?.organization_id?.slice(0, 8)}...</span>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="block text-slate-500 text-[11px]">Organization Name</span>
                <span className="font-semibold text-slate-900 text-sm">{organization?.organization_name}</span>
              </div>

              <div>
                <span className="block text-slate-500 text-[11px]">Official Operations Email</span>
                <div className="flex items-center space-x-1.5 mt-0.5">
                  <span className="font-mono text-slate-700">{organization?.official_email}</span>
                  {organization?.email_verified && (
                    <span className="inline-flex items-center space-x-0.5 px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
                      <CheckCircle2 className="w-3 h-3 mr-0.5" />
                      VERIFIED
                    </span>
                  )}
                </div>
              </div>

              <div>
                <span className="block text-slate-500 text-[11px]">Industry Classification</span>
                <span className="text-slate-800 font-medium">{organization?.industry}</span>
              </div>

              <div>
                <span className="block text-slate-500 text-[11px]">Operational Headquarters</span>
                <span className="text-slate-800 font-medium">{organization?.location}</span>
              </div>

              <div>
                <span className="block text-slate-500 text-[11px]">Enrollment Timestamp</span>
                <span className="font-mono text-slate-600 text-[11px]">{formatDate(organization?.created_at)}</span>
              </div>
            </div>
          </div>

          {/* Panel 2: Energy Workspace & Auth Protocol */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2 text-xs font-mono text-slate-800 font-bold uppercase tracking-wider">
                <Lock className="w-4 h-4 text-emerald-600" />
                <span>Workspace Access</span>
              </div>
              <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200 font-semibold">
                ACTIVE
              </span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl bg-teal-50/50 border border-teal-100">
                <span className="block text-[11px] font-mono text-slate-500 mb-1">
                  NORMAL LOGIN IDENTIFIER:
                </span>
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-teal-800 text-sm tracking-wider">
                    {organization?.registration_id}
                  </span>
                  <span className="text-[10px] text-teal-700 font-mono font-medium">NON-EMAIL AUTH</span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between text-slate-700 py-1 border-b border-slate-100">
                  <span>Password Hash</span>
                  <span className="font-mono text-slate-500">BCRYPT-BLOWFISH-12</span>
                </div>
                <div className="flex items-center justify-between text-slate-700 py-1 border-b border-slate-100">
                  <span>Session Token</span>
                  <span className="font-mono text-slate-500">JWT / HS256</span>
                </div>
                <div className="flex items-center justify-between text-slate-700 py-1 border-b border-slate-100">
                  <span>Session Lifetime</span>
                  <span className="font-mono text-slate-500">24 Hours (Rolling)</span>
                </div>
                <div className="flex items-center justify-between text-slate-700 py-1">
                  <span>Email Verification State</span>
                  <span className="font-mono text-emerald-700 font-semibold">VERIFIED</span>
                </div>
              </div>
            </div>
          </div>

          {/* Panel 3: Quick Operations */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                <div className="flex items-center space-x-2 text-xs font-mono text-slate-800 font-bold uppercase tracking-wider">
                  <Activity className="w-4 h-4 text-teal-600" />
                  <span>Workspace Actions</span>
                </div>
                <span className="text-[10px] font-mono text-emerald-700 font-semibold">ONLINE</span>
              </div>

              <div className="space-y-2.5">
                <button
                  onClick={handleCopyId}
                  className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-800 text-xs font-mono transition-colors cursor-pointer"
                >
                  <span className="flex items-center space-x-2">
                    <Copy className="w-3.5 h-3.5 text-teal-600" />
                    <span>Copy Registration ID</span>
                  </span>
                  <span className="text-teal-700 font-bold">{organization?.registration_id}</span>
                </button>

                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-600 text-[11px] leading-relaxed">
                  <p className="font-semibold text-slate-800 mb-1">Session Protocol:</p>
                  To switch facility contexts or end your session, click Sign Out below to revoke active access tokens.
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100">
              <button
                onClick={handleLogout}
                className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-mono font-medium tracking-wider transition-colors cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
                <span>SIGN OUT OF WORKSPACE</span>
              </button>
            </div>
          </div>
        </div>

        {/* Industrial Energy Telemetry & Audit Stream */}
        <div className="bg-slate-900 rounded-2xl p-5 border border-slate-800 shadow-xl font-mono text-xs text-slate-300">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
            <div className="flex items-center space-x-2 text-slate-300">
              <Terminal className="w-4 h-4 text-amber-400" />
              <span className="font-bold text-white uppercase tracking-widest text-[11px]">
                RESK Energy Telemetry & Activity Stream
              </span>
            </div>
            <div className="flex items-center space-x-2 text-[10px] text-slate-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>GRID_TELEMETRY_SYNC</span>
            </div>
          </div>

          <div className="space-y-1.5 text-slate-400 text-[11px]">
            <p className="text-slate-500">[2026-10-01 12:00:00 UTC] ENERGY_PLATFORM: Telemetry daemon active on port 8000.</p>
            <p className="text-slate-500">[2026-10-01 12:00:01 UTC] PEAK_SHAVE_ENGINE: Real-time load analysis synchronized.</p>
            <p className="text-emerald-400">
              [{new Date().toISOString()}] WORKSPACE_SESSION: Organization {organization?.registration_id} ({organization?.organization_name}) authenticated.
            </p>
            <p className="text-amber-400">
              [{new Date().toISOString()}] FACILITY_ACCESS: Endpoint /auth/me queried with valid Bearer token.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
