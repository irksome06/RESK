import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { CheckCircle2, AlertTriangle, ArrowRight, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import AuthLayout from '../components/AuthLayout';

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
    <AuthLayout>
      <div className="w-full space-y-4">
        <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-xl shadow-slate-200/50 relative overflow-hidden border border-slate-200">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-teal-600 via-amber-400 to-emerald-500"></div>

          {/* Heading */}
          <div className="mb-6 space-y-1">
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono uppercase bg-teal-50 text-teal-800 border border-teal-200 font-semibold">
                Email Authentication
              </span>
            </div>
            <h2
              className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 uppercase"
              style={{ fontFamily: 'var(--font-display, sans-serif)' }}
            >
              EMAIL VERIFICATION
            </h2>
            <p className="text-xs sm:text-sm text-slate-600">
              Verify your official company email to activate your energy workspace
            </p>
          </div>

          {status === 'success' ? (
            <div className="text-center space-y-5 py-4">
              <div className="inline-flex p-3 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600">
                <CheckCircle2 className="w-10 h-10" />
              </div>

              <div>
                <h3 className="text-lg font-bold text-slate-900 uppercase tracking-wider font-mono">
                  Verification Confirmed
                </h3>
                <p className="text-xs text-slate-600 mt-2">{message}</p>
                {verifiedRegId && (
                  <p className="text-xs font-mono text-teal-800 mt-2 bg-teal-50 p-2.5 rounded-xl border border-teal-200">
                    {verifiedRegId}
                  </p>
                )}
              </div>

              <div className="pt-2">
                <button
                  onClick={() => navigate('/login')}
                  className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold text-xs uppercase tracking-wider transition-all cursor-pointer shadow-md shadow-amber-400/25"
                >
                  <span>Proceed to Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {status === 'error' && (
                <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 flex items-start space-x-2.5 text-red-800 text-xs">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-600" />
                  <p className="font-medium">{message}</p>
                </div>
              )}

              {/* Option A: Email + Code */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  Official Company Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="operations@company.com"
                  className="block w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  6-Digit Verification Code
                </label>
                <input
                  type="text"
                  maxLength="6"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="123456"
                  className="block w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm font-mono tracking-widest text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600"
                />
              </div>

              <div className="relative py-2 flex items-center justify-center">
                <div className="border-t border-slate-200 w-full absolute"></div>
                <span className="bg-white px-3 text-[10px] font-mono text-slate-400 relative uppercase">
                  OR VERIFY VIA TOKEN
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  Direct Verification Token
                </label>
                <input
                  type="text"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="Paste verification token string..."
                  className="block w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-xs font-mono text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={status === 'verifying'}
                  className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-md shadow-amber-400/25 transition-all cursor-pointer disabled:opacity-50"
                >
                  {status === 'verifying' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Validating Verification Token...</span>
                    </>
                  ) : (
                    <>
                      <span>Confirm Verification</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              <div className="pt-3 border-t border-slate-100 text-center">
                <Link to="/login" className="text-xs text-teal-700 hover:text-teal-800 font-medium">
                  Return to Sign In
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </AuthLayout>
  );
}
