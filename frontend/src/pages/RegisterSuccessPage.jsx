import React, { useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import {
  ShieldCheck,
  Copy,
  Check,
  ArrowRight,
  AlertTriangle,
  Building,
  KeyRound,
  Download,
} from 'lucide-react';

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
RESK INDUSTRIAL DEFENSE PLATFORM - ORGANIZATION CREDENTIALS
=====================================================
Organization Name: ${orgName}
Official Email:    ${email}
Registration ID:   ${regId}
=====================================================
IMPORTANT NOTICE:
Your unique Organization Registration ID is REQUIRED for all normal logins.
Email or phone numbers cannot be used for sign in. Keep this ID safe.
=====================================================`;

    const blob = new Blob([textContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${regId}_RESK_Credentials.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-industrial-grid">
      <div className="w-full max-w-lg space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-400 mb-1">
            <ShieldCheck className="w-10 h-10" />
          </div>
          <h1
            className="text-2xl sm:text-3xl font-bold tracking-wider text-white uppercase"
            style={{ fontFamily: 'var(--font-display, sans-serif)' }}
          >
            Registration Complete
          </h1>
          <p className="text-xs text-slate-400 font-mono tracking-wide uppercase">
            Facility Credential Initialized
          </p>
        </div>

        {/* Success Card */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-amber-400 to-amber-600"></div>

          {/* Org details summary */}
          <div className="mb-6 p-4 rounded-lg bg-slate-950/80 border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Organization Name:</span>
              <span className="font-semibold text-slate-200">{orgName}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Official Email:</span>
              <span className="font-mono text-slate-300">{email}</span>
            </div>
          </div>

          {/* REGISTRATION ID HERO DISPLAY */}
          <div className="text-center py-5 px-4 bg-slate-950/90 rounded-xl border-2 border-amber-500/40 glow-amber relative">
            <span className="inline-block px-2.5 py-0.5 rounded text-[10px] font-mono uppercase bg-amber-500/10 text-amber-400 border border-amber-500/30 mb-2">
              Assigned Registration Identifier
            </span>

            <div className="text-3xl sm:text-4xl font-mono font-bold tracking-[0.2em] text-amber-400 py-1 select-all">
              {regId}
            </div>

            <p className="text-xs text-slate-400 font-mono mt-1">
              Your unique enterprise identifier
            </p>

            {/* Action buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-2 mt-4 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={handleCopy}
                className="w-full sm:w-auto flex items-center justify-center space-x-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white text-xs font-mono font-medium transition-colors cursor-pointer border border-slate-700"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4 text-emerald-400" />
                    <span className="text-emerald-400">COPIED TO CLIPBOARD!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 text-amber-400" />
                    <span>Copy Registration ID</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={handleDownloadBackup}
                className="w-full sm:w-auto flex items-center justify-center space-x-1.5 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-mono transition-colors border border-slate-800"
              >
                <Download className="w-3.5 h-3.5 text-slate-400" />
                <span>Save Backup .txt</span>
              </button>
            </div>
          </div>

          {/* CRITICAL SECURITY NOTICE */}
          <div className="mt-6 p-3.5 rounded-lg bg-amber-950/30 border border-amber-500/30 flex items-start space-x-3 text-xs text-amber-200">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-400 mt-0.5" />
            <div className="space-y-1">
              <p className="font-bold text-amber-300 font-mono uppercase tracking-wide">
                AUTHENTICATION RULE:
              </p>
              <p className="text-amber-200/90 leading-relaxed">
                Normal sign-in <strong>strictly requires</strong> this Registration ID + your password.
                The official email is <strong>NOT</strong> an accepted login identifier.
              </p>
            </div>
          </div>

          {/* Proceed to Login Button */}
          <div className="mt-6">
            <button
              onClick={() =>
                navigate('/login', {
                  state: {
                    registration_id: regId,
                    message: `Registration ID ${regId} copied into form. Enter password to access.`,
                  },
                })
              }
              className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-amber-500/20 transition-all cursor-pointer"
            >
              <span>Proceed to Sign In with {regId}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
