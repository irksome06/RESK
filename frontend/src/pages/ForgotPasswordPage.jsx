import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, ArrowRight, ArrowLeft, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import AuthLayout from '../components/AuthLayout';

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
    <AuthLayout>
      <div className="w-full space-y-4">
        <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-xl shadow-slate-200/50 relative overflow-hidden border border-slate-200">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-teal-600 via-amber-400 to-emerald-500"></div>

          {/* Heading */}
          <div className="mb-6 space-y-1">
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono uppercase bg-teal-50 text-teal-800 border border-teal-200 font-semibold">
                Credential Recovery
              </span>
            </div>
            <h2
              className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 uppercase"
              style={{ fontFamily: 'var(--font-display, sans-serif)' }}
            >
              PASSWORD RECOVERY
            </h2>
            <p className="text-xs sm:text-sm text-slate-600">
              Recover access to your organization's energy workspace
            </p>
          </div>

          {submitted ? (
            <div className="space-y-5 text-center py-2">
              <div className="inline-flex p-3 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-900 uppercase tracking-wide">
                  Reset Instructions Sent
                </h3>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                  {responseMsg || 'If this company email is registered in the RESK platform, password reset instructions have been dispatched.'}
                </p>
              </div>

              {/* Dev token testing helper */}
              {devResetToken && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-left text-xs font-mono text-amber-900">
                  <p className="font-bold mb-1">[DEVELOPMENT DISPATCH CAPTURED]</p>
                  <p className="text-[11px] text-slate-600 truncate mb-2">Token: {devResetToken}</p>
                  <Link
                    to={`/reset-password?token=${devResetToken}`}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold font-sans text-xs transition-colors shadow-2xs"
                  >
                    <span>Proceed to Reset Password</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              )}

              <div className="pt-3 border-t border-slate-100">
                <Link
                  to="/login"
                  className="inline-flex items-center space-x-2 text-xs text-teal-700 hover:text-teal-800 font-semibold"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Return to Sign In</span>
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 flex items-start space-x-2.5 text-red-800 text-xs">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-600" />
                  <p className="font-medium">{error}</p>
                </div>
              )}

              <p className="text-xs text-slate-600 leading-relaxed">
                Enter your registered official company email address. We will verify your organization records and dispatch a secure reset token.
              </p>

              <div>
                <label
                  htmlFor="email"
                  className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                >
                  Official Company Email
                </label>
                <div className="relative rounded-lg shadow-2xs">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Mail className="h-4 w-4 text-teal-600" />
                  </div>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="operations@company.com"
                    required
                    autoFocus
                    className="block w-full pl-10 pr-4 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 font-mono transition-all"
                  />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-md shadow-amber-400/25 transition-all cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Sending Reset Link...</span>
                    </>
                  ) : (
                    <>
                      <span>Dispatch Reset Link</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              <div className="pt-3 border-t border-slate-100 text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center space-x-1.5 text-xs text-slate-600 hover:text-teal-700 transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to Sign In</span>
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </AuthLayout>
  );
}
