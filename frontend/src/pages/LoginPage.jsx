import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Shield, KeyRound, ArrowRight, AlertTriangle, Building, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import PasswordInput from '../components/PasswordInput';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  // Support prefilling registration_id from registration success page
  const initialRegId = location.state?.registration_id || '';
  const successNotice = location.state?.message || '';

  const [registrationId, setRegistrationId] = useState(initialRegId);
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const cleanId = registrationId.trim().toUpperCase();
    if (!cleanId) {
      setError('Please provide your Organization Registration ID (e.g. RESK-7F42K9).');
      return;
    }

    if (!password) {
      setError('Please enter your password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login(cleanId, password, rememberMe);
      const redirectPath = location.state?.from?.pathname || '/dashboard';
      navigate(redirectPath, { replace: true });
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 relative bg-industrial-grid">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-slate-900/90 border border-amber-500/30 glow-amber mb-2">
            <Shield className="w-8 h-8 text-amber-400" />
          </div>
          <h1
            className="text-2xl sm:text-3xl font-bold tracking-wider text-white uppercase"
            style={{ fontFamily: 'var(--font-display, sans-serif)' }}
          >
            RESK Industrial
          </h1>
          <p className="text-xs text-slate-400 font-mono tracking-wide uppercase">
            Organization Identity & Access Portal
          </p>
        </div>

        {/* Notice from previous step if any */}
        {successNotice && (
          <div className="p-3.5 rounded-lg bg-emerald-950/40 border border-emerald-500/40 flex items-start space-x-2.5 text-emerald-300 text-xs">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5 text-emerald-400" />
            <div>
              <p className="font-semibold">{successNotice}</p>
              <p className="text-emerald-400/80 mt-0.5">Please sign in with your Registration ID and password.</p>
            </div>
          </div>
        )}

        {/* Form Card */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl relative overflow-hidden">
          {/* Top highlight bar */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-500 via-amber-400 to-amber-600"></div>

          {error && (
            <div className="mb-5 p-3.5 rounded-lg bg-red-950/50 border border-red-500/40 flex items-start space-x-2.5 text-red-200 text-xs">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-400" />
              <div>
                <p className="font-medium">{error}</p>
                {error.includes('not yet verified') && (
                  <Link
                    to="/register/verify"
                    state={{ registration_id: registrationId }}
                    className="inline-block mt-1 text-amber-400 hover:underline font-mono text-[11px]"
                  >
                    Click here to enter your email verification code →
                  </Link>
                )}
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Organization Registration ID */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label
                  htmlFor="registrationId"
                  className="block text-xs font-semibold uppercase tracking-wider text-slate-400"
                >
                  Organization Registration ID
                </label>
                <span className="text-[10px] font-mono text-amber-400/90 bg-amber-400/10 px-1.5 py-0.5 rounded border border-amber-400/20">
                  REQUIRED
                </span>
              </div>
              <div className="relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <KeyRound className="h-4 w-4" />
                </div>
                <input
                  id="registrationId"
                  name="registrationId"
                  type="text"
                  value={registrationId}
                  onChange={(e) => setRegistrationId(e.target.value.toUpperCase())}
                  placeholder="RESK-7F42K9"
                  required
                  autoFocus={!initialRegId}
                  className="block w-full pl-10 pr-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-amber-400 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/80 font-mono tracking-widest uppercase transition-all"
                />
              </div>
              <p className="mt-1 text-[11px] text-slate-500 font-mono">
                Normal sign-in uses your unique Registration ID. Do not use email.
              </p>
            </div>

            {/* Master Password */}
            <div>
              <PasswordInput
                id="password"
                name="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                label="Master Password"
                placeholder="••••••••••••"
              />
            </div>

            {/* Remember Me & Forgot Password */}
            <div className="flex items-center justify-between text-xs pt-1">
              <label className="flex items-center space-x-2 cursor-pointer select-none text-slate-400 hover:text-slate-300">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 rounded bg-slate-950 border-slate-700 text-amber-500 focus:ring-amber-500/40 focus:ring-offset-0 focus:ring-1"
                />
                <span>Remember Session</span>
              </label>

              <Link
                to="/forgot-password"
                className="text-amber-400 hover:text-amber-300 font-medium transition-colors"
              >
                Forgot Password?
              </Link>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-amber-500/20 hover:shadow-amber-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isSubmitting ? (
                <span>Validating Clearance...</span>
              ) : (
                <>
                  <span>Sign In To Organization</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Registration link */}
          <div className="mt-6 pt-5 border-t border-slate-800/80 text-center">
            <p className="text-xs text-slate-400">
              Need access for a new facility?{' '}
              <Link
                to="/register"
                className="text-amber-400 hover:text-amber-300 font-semibold inline-flex items-center space-x-1"
              >
                <span>Register Organization</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </p>
          </div>
        </div>

        {/* Security notice footer */}
        <div className="text-center">
          <p className="text-[11px] font-mono text-slate-500">
            ENCRYPTED DISPATCH // ZERO TRUST IDENTITY ENFORCED
          </p>
        </div>
      </div>
    </div>
  );
}
