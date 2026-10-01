import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Shield, ShieldAlert, LogOut, LayoutDashboard, Building2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
  const { organization, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <Link to={isAuthenticated ? '/dashboard' : '/login'} className="flex items-center space-x-3 group">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500/20 to-amber-600/10 border border-amber-500/40 flex items-center justify-center shadow-lg shadow-amber-500/10 group-hover:border-amber-400 transition-colors">
              <Shield className="w-5 h-5 text-amber-400 group-hover:scale-105 transition-transform" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-widest text-white uppercase" style={{ fontFamily: 'var(--font-display, sans-serif)' }}>
                  RESK
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  ORG_AUTH
                </span>
              </div>
              <span className="block text-[10px] tracking-wider text-slate-400 font-mono -mt-1 uppercase">
                Enterprise Defense Core
              </span>
            </div>
          </Link>

          {/* System status pill */}
          <div className="hidden md:flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>NODE_READY // PROTOCOL v1.0</span>
          </div>

          {/* Nav Actions */}
          <div className="flex items-center space-x-3">
            {isAuthenticated ? (
              <div className="flex items-center space-x-3">
                <div className="hidden sm:flex flex-col text-right">
                  <span className="text-xs font-semibold text-slate-200">
                    {organization?.organization_name}
                  </span>
                  <span className="text-[11px] font-mono text-amber-400">
                    {organization?.registration_id}
                  </span>
                </div>
                <Link
                  to="/dashboard"
                  className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 transition-colors"
                  title="Dashboard"
                >
                  <LayoutDashboard className="w-4 h-4" />
                </Link>
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-red-950/30 border border-red-900/50 text-red-300 hover:bg-red-900/50 hover:text-red-100 text-xs font-mono transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">DISCONNECT</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-3">
                <Link
                  to="/login"
                  className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-semibold tracking-wide shadow-md shadow-amber-500/20 transition-all"
                >
                  <Building2 className="w-3.5 h-3.5" />
                  <span>Register Org</span>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
