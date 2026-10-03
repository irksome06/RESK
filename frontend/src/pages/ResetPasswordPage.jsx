import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { CheckCircle2, AlertTriangle, ArrowRight, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import PasswordInput from '../components/PasswordInput';
import PasswordStrengthIndicator from '../components/PasswordStrengthIndicator';
import AuthLayout from '../components/AuthLayout';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const tokenFromUrl = searchParams.get('token') || '';

  const [resetToken, setResetToken] = useState(tokenFromUrl);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (tokenFromUrl) {
      setResetToken(tokenFromUrl);
    }
  }, [tokenFromUrl]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!resetToken.trim()) {
      setError('A valid password reset token is required.');
      return;
    }
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await api.resetPassword(resetToken.trim(), newPassword, confirmPassword);
      setSuccess(true);
    } catch (err) {
      setError(err.message || 'Failed to reset password. The token may be expired or already used.');
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
                Credential Reset
              </span>
            </div>
            <h2
              className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 uppercase"
              style={{ fontFamily: 'var(--font-display, sans-serif)' }}
            >
              RESET PASSWORD
            </h2>
            <p className="text-xs sm:text-sm text-slate-600">
              Establish a new password for your organization's energy workspace
            </p>
          </div>

          {success ? (
            <div className="space-y-5 text-center py-2">
              <div className="inline-flex p-3 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-900 uppercase tracking-wide">
                  Password Updated
                </h3>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                  Your organization's password has been updated. You can now authenticate with your Registration ID and new password.
                </p>
              </div>

              <div className="pt-2">
                <button
                  onClick={() =>
                    navigate('/login', {
                      state: { message: 'Password updated. Sign in with your Registration ID.' },
                    })
                  }
                  className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold text-xs uppercase tracking-wider transition-all cursor-pointer shadow-md shadow-amber-400/25"
                >
                  <span>Proceed to Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
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

              {/* Reset Token */}
              <div>
                <label
                  htmlFor="resetToken"
                  className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                >
                  Reset Token
                </label>
                <input
                  id="resetToken"
                  type="text"
                  value={resetToken}
                  onChange={(e) => setResetToken(e.target.value)}
                  placeholder="Paste reset token string..."
                  required
                  className="block w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-xs font-mono text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600"
                />
              </div>

              {/* New Password */}
              <div>
                <PasswordInput
                  id="newPassword"
                  name="newPassword"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  label="New Password"
                  placeholder="Enter new password"
                />
                <PasswordStrengthIndicator password={newPassword} />
              </div>

              {/* Confirm New Password */}
              <div className="pt-1">
                <PasswordInput
                  id="confirmPassword"
                  name="confirmPassword"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  label="Confirm New Password"
                  placeholder="Repeat new password"
                  error={
                    confirmPassword && newPassword !== confirmPassword ? 'Passwords do not match' : ''
                  }
                />
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
                      <span>Updating Password...</span>
                    </>
                  ) : (
                    <>
                      <span>Set New Password</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              <div className="pt-3 border-t border-slate-100 text-center">
                <Link to="/login" className="text-xs text-teal-700 hover:text-teal-800 font-medium">
                  Cancel and Return to Sign In
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </AuthLayout>
  );
}
