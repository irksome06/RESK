import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { LogOut, LayoutDashboard, Building2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import ReskLogo from './ReskLogo';

export default function Navbar() {
  const { organization, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // On login page, the immersive full-width layout has its own integrated header
  if (location.pathname === '/login') {
    return null;
  }

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="border-b border-slate-200/90 bg-white/95 backdrop-blur-md sticky top-0 z-50 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <Link to={isAuthenticated ? '/dashboard' : '/login'} className="flex items-center space-x-3 group">
            <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center shadow-xs group-hover:border-teal-400 transition-all">
              <ReskLogo className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-tight text-slate-900" style={{ fontFamily: 'var(--font-display, sans-serif)' }}>
                  RESK
                </span>
                <span className="text-slate-300">|</span>
                <span className="text-xs font-medium text-slate-500">
                  Energy Intelligence Platform
                </span>
              </div>
            </div>
          </Link>

          {/* Grid telemetry status pill */}
          <div className="hidden md:flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-100/80 border border-slate-200 text-xs font-mono text-slate-700">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-[11px] text-slate-500">System Online</span>
            <span className="text-slate-300">|</span>
            <span className="text-emerald-700 font-semibold text-[11px]">v1.0</span>
          </div>

          {/* Nav Actions */}
          <div className="flex items-center space-x-3">
            {isAuthenticated ? (
              <div className="flex items-center space-x-3">
                <div className="hidden sm:flex flex-col text-right">
                  <span className="text-xs font-semibold text-slate-900">
                    {organization?.organization_name}
                  </span>
                  <span className="text-[11px] font-mono font-medium text-teal-700">
                    {organization?.registration_id}
                  </span>
                </div>
                <Link
                  to="/dashboard"
                  className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 transition-colors"
                  title="Energy Dashboard"
                >
                  <LayoutDashboard className="w-4 h-4" />
                </Link>
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-medium transition-colors cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Sign Out</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-3">
                <Link
                  to="/login"
                  className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-teal-700 transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-[#F5B515] hover:bg-[#E5A70A] text-slate-950 text-xs font-bold tracking-wide shadow-xs hover:shadow transition-all cursor-pointer"
                >
                  <Building2 className="w-3.5 h-3.5 text-slate-900" />
                  <span>Set Up Workspace</span>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
