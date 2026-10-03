import React, { useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import {
  CheckCircle2,
  Copy,
  Check,
  ArrowRight,
  AlertTriangle,
  Download,
} from 'lucide-react';
import AuthLayout from '../components/AuthLayout';

export default function RegisterSuccessPage() {
  const location = useLocation();
  const navigate = useNavigate();

  // Retrieve passed state or fallback for direct visits
  const regId = location.state?.registration_id || 'RESK-7F42K9';
  const orgName = location.state?.organization_name || 'Registered Organization';
  const email = location.state?.official_email || 'organization@enterprise.com';

  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(regId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleDownloadBackup = () => {
    const textContent = `=====================================================
RESK INDUSTRIAL ENERGY OPTIMIZATION PLATFORM
ORGANIZATION CREDENTIAL BACKUP
=====================================================
Organization Name: ${orgName}
Official Email:    ${email}
Registration ID:   ${regId}
=====================================================
CRITICAL AUTHENTICATION NOTICE:
Your Organization Registration ID is REQUIRED for all normal logins.
Normal login uses Registration ID + Password.
Official email is reserved for password recovery and alerts.
Keep this Registration ID in a safe place.
=====================================================`;

    const blob = new Blob([textContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${regId}_RESK_Energy_Credentials.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <AuthLayout>
      <div className="w-full space-y-4">
        {/* Success Card */}
        <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-xl shadow-slate-200/50 relative overflow-hidden border border-slate-200">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-teal-600 via-amber-400 to-emerald-500"></div>

          {/* Heading */}
          <div className="mb-6 space-y-1">
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono uppercase bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1 font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Workspace Active</span>
              </span>
            </div>
            <h2
              className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 uppercase"
              style={{ fontFamily: 'var(--font-display, sans-serif)' }}
            >
              ENERGY WORKSPACE INITIALIZED
            </h2>
            <p className="text-xs sm:text-sm text-slate-600">
              Your organization is registered with RESK Energy Intelligence
            </p>
          </div>

          {/* Org details summary */}
          <div className="mb-5 p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500">Organization:</span>
              <span className="font-semibold text-slate-900">{orgName}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500">Official Email:</span>
              <span className="font-mono text-slate-800">{email}</span>
            </div>
          </div>

          {/* REGISTRATION ID HERO DISPLAY */}
          <div className="text-center py-5 px-4 bg-teal-50/50 rounded-xl border-2 border-teal-200 relative">
            <span className="inline-block px-2.5 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-teal-100 text-teal-800 border border-teal-300 mb-1.5">
              Assigned Registration Identifier
            </span>

            <div className="text-3xl sm:text-4xl font-mono font-bold tracking-[0.2em] text-slate-900 py-1 select-all">
              {regId}
            </div>

            <p className="text-xs text-slate-600 mt-1">
              Your unique energy workspace identifier
            </p>

            {/* Action buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-2 mt-4 pt-3 border-t border-teal-100">
              <button
                type="button"
                onClick={handleCopy}
                className="w-full sm:w-auto flex items-center justify-center space-x-2 px-4 py-2 rounded-lg bg-white hover:bg-slate-50 text-slate-800 text-xs font-mono font-medium transition-colors cursor-pointer border border-slate-300 shadow-2xs"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4 text-emerald-600" />
                    <span className="text-emerald-700 font-bold">COPIED TO CLIPBOARD!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 text-teal-600" />
                    <span>Copy Registration ID</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={handleDownloadBackup}
                className="w-full sm:w-auto flex items-center justify-center space-x-1.5 px-3 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-mono transition-colors border border-slate-200 cursor-pointer"
              >
                <Download className="w-3.5 h-3.5 text-slate-500" />
                <span>Save Credentials (.txt)</span>
              </button>
            </div>
          </div>

          {/* CRITICAL AUTHENTICATION NOTICE */}
          <div className="mt-5 p-3.5 rounded-xl bg-amber-50 border border-amber-200 flex items-start space-x-3 text-xs text-amber-900">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-600 mt-0.5" />
            <div className="space-y-0.5">
              <p className="font-bold text-amber-900 font-mono uppercase text-[11px] tracking-wide">
                AUTHENTICATION RULE:
              </p>
              <p className="text-amber-800 leading-relaxed text-[11px]">
                Normal sign-in requires this <strong className="text-amber-950 font-bold">Registration ID</strong> + your password. Email addresses cannot be used for normal sign-in.
              </p>
            </div>
          </div>

          {/* Proceed to Login Button */}
          <div className="mt-5">
            <button
              onClick={() =>
                navigate('/login', {
                  state: {
                    registration_id: regId,
                    message: `Registration ID ${regId} pre-filled. Enter your password to access.`,
                  },
                })
              }
              className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-md shadow-amber-400/25 transition-all cursor-pointer"
            >
              <span>Proceed to Sign In with {regId}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </AuthLayout>
  );
}
