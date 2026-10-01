import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { KeyRound, Mail, ArrowRight, ArrowLeft, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import { api } from '../services/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [responseMsg, setResponseMsg] = useState('');
  const [devResetToken, setDevResetToken] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setError('Please provide a valid company email address.');
      return;
    }

    setIsSubmitting(true);
    try {
      const resp = await api.forgotPassword(cleanEmail);
      setSubmitted(true);
      setResponseMsg(resp.message);
      if (resp.dev_token) {
        setDevResetToken(resp.dev_token);
      }
    } catch (err) {
      setError(err.message || 'Unable to process reset request. Please retry.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-industrial-grid">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-slate-900/90 border border-amber-500/30 glow-amber mb-1">
            <KeyRound className="w-8 h-8 text-amber-400" />
          </div>
          <h1
            className="text-2xl sm:text-3xl font-bold tracking-wider text-white uppercase"
            style={{ fontFamily: 'var(--font-display, sans-serif)' }}
          >
            Password Recovery
          </h1>
          <p className="text-xs text-slate-400 font-mono tracking-wide uppercase">
            Official Organization Email Verification
          </p>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-500 via-amber-400 to-amber-600"></div>

          {submitted ? (
            <div className="space-y-5 text-center py-2">
              <div className="inline-flex p-3 rounded-full bg-emerald-950/60 border border-emerald-500/40 text-emerald-400">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div>
                <h3 className="text-base font-bold text-white font-mono uppercase tracking-wide">
                  Dispatch Dispatched
                </h3>
                <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                  {responseMsg || 'If this company email is registered in the RESK platform, password reset instructions and a secure temporary link have been dispatched.'}
                </p>
              </div>

              {/* Dev token testing helper */}
              {devResetToken && (
                <div className="p-3 bg-amber-950/40 border border-amber-500/40 rounded-lg text-left text-xs font-mono text-amber-300">
                  <p className="font-bold mb-1">[DEVELOPMENT DISPATCH CAPTURED]</p>
                  <p className="text-[11px] text-slate-400 truncate mb-2">Token: {devResetToken}</p>
                  <Link
                    to={`/reset-password?token=${devResetToken}`}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold font-sans text-xs transition-colors"
                  >
                    <span>Proceed to Reset Password</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              )}

              <div className="pt-3 border-t border-slate-800/80">
                <Link
                  to="/login"
                  className="inline-flex items-center space-x-2 text-xs font-mono text-amber-400 hover:text-amber-300 font-semibold"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Return to Sign In</span>
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3.5 rounded-lg bg-red-950/50 border border-red-500/40 flex items-start space-x-2.5 text-red-200 text-xs">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-400" />
                  <p className="font-medium">{error}</p>
                </div>
              )}

              <p className="text-xs text-slate-400 leading-relaxed">
                Enter your registered official company email address. We will generate a secure reset token valid for 15 minutes.
              </p>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Official Company Email
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Mail className="h-4 w-4" />
                  </div>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="security@enterprise.com"
                    required
                    autoFocus
                    className="block w-full pl-10 pr-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/80 font-mono"
                  />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-amber-500/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Generating Secure Token...</span>
                    </>
                  ) : (
                    <>
                      <span>Request Password Reset</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              <div className="pt-4 border-t border-slate-800/80 text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center space-x-1.5 text-xs text-slate-400 hover:text-amber-400 transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Return to Sign In</span>
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
