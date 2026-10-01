import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { MailCheck, CheckCircle2, AlertTriangle, ArrowRight, Loader2, Shield } from 'lucide-react';
import { api } from '../services/api';

export default function RegisterVerifyPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const tokenParam = searchParams.get('token') || '';
  const emailParam = searchParams.get('email') || '';
  const codeParam = searchParams.get('code') || '';

  const [email, setEmail] = useState(emailParam);
  const [code, setCode] = useState(codeParam);
  const [token, setToken] = useState(tokenParam);
  const [status, setStatus] = useState('idle'); // idle, verifying, success, error
  const [message, setMessage] = useState('');
  const [verifiedRegId, setVerifiedRegId] = useState('');

  // Auto-verify if full query parameters are present
  useEffect(() => {
    if (tokenParam || (emailParam && codeParam)) {
      handleVerification(tokenParam, emailParam, codeParam);
    }
  }, []);

  const handleVerification = async (verifyToken, verifyEmail, verifyCode) => {
    setStatus('verifying');
    setMessage('');

    try {
      const resp = await api.verifyEmail({
        token: verifyToken || token || undefined,
        email: verifyEmail || email || undefined,
        code: verifyCode || code || undefined,
      });

      setStatus('success');
      setMessage(resp.message || 'Email successfully verified.');
      if (resp.detail) {
        setVerifiedRegId(resp.detail);
      }
    } catch (err) {
      setStatus('error');
      setMessage(err.message || 'Email verification failed. The code or token may be expired.');
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!token && (!email || !code)) {
      setStatus('error');
      setMessage('Please provide either your verification token or your registered email and 6-digit code.');
      return;
    }
    handleVerification(token, email, code);
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-industrial-grid">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-slate-900/90 border border-amber-500/30 glow-amber mb-1">
            <MailCheck className="w-8 h-8 text-amber-400" />
          </div>
          <h1
            className="text-2xl sm:text-3xl font-bold tracking-wider text-white uppercase"
            style={{ fontFamily: 'var(--font-display, sans-serif)' }}
          >
            Email Verification
          </h1>
          <p className="text-xs text-slate-400 font-mono tracking-wide uppercase">
            RESK Defense Clearance Verification
          </p>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-500 via-amber-400 to-amber-600"></div>

          {status === 'success' ? (
            <div className="text-center space-y-5 py-4">
              <div className="inline-flex p-3 rounded-full bg-emerald-950/60 border border-emerald-500/40 text-emerald-400">
                <CheckCircle2 className="w-10 h-10" />
              </div>

              <div>
                <h3 className="text-lg font-bold text-white uppercase tracking-wider font-mono">
                  Verification Confirmed
                </h3>
                <p className="text-xs text-slate-300 mt-2">{message}</p>
                {verifiedRegId && (
                  <p className="text-xs font-mono text-amber-400 mt-2 bg-slate-950 p-2 rounded border border-slate-800">
                    {verifiedRegId}
                  </p>
                )}
              </div>

              <div className="pt-2">
                <button
                  onClick={() => navigate('/login', { state: { message: 'Email verified successfully.' } })}
                  className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wider transition-all cursor-pointer shadow-lg shadow-amber-500/20"
                >
                  <span>Proceed to Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {status === 'error' && (
                <div className="p-3.5 rounded-lg bg-red-950/50 border border-red-500/40 flex items-start space-x-2.5 text-red-200 text-xs">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-400" />
                  <p className="font-medium">{message}</p>
                </div>
              )}

              <p className="text-xs text-slate-400">
                Enter the 6-digit verification code sent to your company email address.
              </p>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Official Company Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="security@company.com"
                  className="block w-full px-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/80 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  6-Digit Verification Code
                </label>
                <input
                  type="text"
                  maxLength="6"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="000000"
                  className="block w-full py-2.5 text-center bg-slate-950/80 border border-slate-800 rounded-lg text-lg text-amber-400 font-mono tracking-[0.4em] focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/80"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={status === 'verifying'}
                  className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wider transition-all cursor-pointer disabled:opacity-50 shadow-lg shadow-amber-500/20"
                >
                  {status === 'verifying' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Verifying Token...</span>
                    </>
                  ) : (
                    <>
                      <span>Verify Email</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              <div className="pt-4 border-t border-slate-800/80 text-center">
                <Link to="/login" className="text-xs text-amber-400 hover:underline font-mono">
                  ← Return to Sign In
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
