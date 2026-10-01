import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Building2,
  Mail,
  Briefcase,
  MapPin,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Send,
  Loader2,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../services/api';
import PasswordInput from '../components/PasswordInput';
import PasswordStrengthIndicator from '../components/PasswordStrengthIndicator';

export default function RegisterPage() {
  const navigate = useNavigate();

  // Wizard state: 1: Details, 2: Verification, 3: Security & Password
  const [currentStep, setCurrentStep] = useState(1);

  // Form Fields
  const [formData, setFormData] = useState({
    organizationName: '',
    officialEmail: '',
    industry: '',
    location: '',
    verificationCode: '',
    password: '',
    confirmPassword: '',
  });

  const [codeSent, setCodeSent] = useState(false);
  const [codeSending, setCodeSending] = useState(false);
  const [devCodeHint, setDevCodeHint] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const industries = [
    'Aerospace & Defense',
    'Industrial Manufacturing',
    'Robotics & Automation',
    'Energy & Power Grid',
    'Automotive & Transport',
    'Chemicals & Materials',
    'Telecommunications & Satellites',
    'Semiconductors & Electronics',
    'Cybersecurity & Infrastructure',
    'Other Industrial Sector',
  ];

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setError('');
  };

  // Step 1: Validate Company Info & Send verification code
  const handleStep1Submit = async (e) => {
    e.preventDefault();
    setError('');

    if (!formData.organizationName.trim()) {
      setError('Organization name is required.');
      return;
    }
    if (!formData.officialEmail.trim() || !formData.officialEmail.includes('@')) {
      setError('A valid official company email is required.');
      return;
    }
    if (!formData.industry) {
      setError('Please select an industry sector.');
      return;
    }
    if (!formData.location.trim()) {
      setError('Headquarters or operational location is required.');
      return;
    }

    // Automatically trigger code send to email
    setCodeSending(true);
    try {
      const resp = await api.sendVerificationCode(formData.officialEmail);
      setCodeSent(true);
      if (resp.dev_token) {
        setDevCodeHint(resp.dev_token);
      }
      setCurrentStep(2);
    } catch (err) {
      setError(err.message || 'Failed to dispatch email verification code. Please check your email.');
    } finally {
      setCodeSending(false);
    }
  };

  // Step 2: Validate Verification Code
  const handleStep2Submit = async (e) => {
    e.preventDefault();
    setError('');

    const cleanCode = formData.verificationCode.trim();
    if (!cleanCode || cleanCode.length < 6) {
      setError('Please enter the 6-digit verification code sent to your official email.');
      return;
    }

    // Proceed to Step 3 (Set Password)
    setCurrentStep(3);
  };

  const handleResendCode = async () => {
    setError('');
    setCodeSending(true);
    try {
      const resp = await api.sendVerificationCode(formData.officialEmail);
      setCodeSent(true);
      if (resp.dev_token) {
        setDevCodeHint(resp.dev_token);
      }
    } catch (err) {
      setError(err.message || 'Failed to resend verification code.');
    } finally {
      setCodeSending(false);
    }
  };

  // Step 3: Validate Password & Complete Registration
  const handleStep3Submit = async (e) => {
    e.preventDefault();
    setError('');

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        organization_name: formData.organizationName.trim(),
        official_email: formData.officialEmail.trim(),
        industry: formData.industry,
        location: formData.location.trim(),
        password: formData.password,
        confirm_password: formData.confirmPassword,
        verification_code: formData.verificationCode.trim(),
      };

      const result = await api.register(payload);

      // Navigate to success page with generated Registration ID
      navigate('/register/success', {
        state: {
          registration_id: result.registration_id,
          organization_name: formData.organizationName,
          official_email: formData.officialEmail,
          email_verified: result.email_verified,
        },
      });
    } catch (err) {
      setError(err.message || 'Organization registration failed. Please review your information.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-10 px-4 sm:px-6 lg:px-8 bg-industrial-grid">
      <div className="w-full max-w-xl space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-slate-900/90 border border-amber-500/30 glow-amber mb-1">
            <Building2 className="w-8 h-8 text-amber-400" />
          </div>
          <h1
            className="text-2xl sm:text-3xl font-bold tracking-wider text-white uppercase"
            style={{ fontFamily: 'var(--font-display, sans-serif)' }}
          >
            Register Organization
          </h1>
          <p className="text-xs text-slate-400 font-mono tracking-wide uppercase">
            Initialize Enterprise Facility Clearance
          </p>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-between px-4 py-3 bg-slate-900/80 border border-slate-800 rounded-xl font-mono text-xs">
          <div className={`flex items-center space-x-2 ${currentStep >= 1 ? 'text-amber-400' : 'text-slate-500'}`}>
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold ${
              currentStep === 1 ? 'bg-amber-500 text-slate-950' : currentStep > 1 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' : 'bg-slate-800 text-slate-400'
            }`}>
              1
            </span>
            <span className="hidden sm:inline">Profile</span>
          </div>

          <div className={`h-0.5 flex-1 mx-3 ${currentStep >= 2 ? 'bg-amber-500/50' : 'bg-slate-800'}`}></div>

          <div className={`flex items-center space-x-2 ${currentStep >= 2 ? 'text-amber-400' : 'text-slate-500'}`}>
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold ${
              currentStep === 2 ? 'bg-amber-500 text-slate-950' : currentStep > 2 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' : 'bg-slate-800 text-slate-400'
            }`}>
              2
            </span>
            <span className="hidden sm:inline">Verify Email</span>
          </div>

          <div className={`h-0.5 flex-1 mx-3 ${currentStep >= 3 ? 'bg-amber-500/50' : 'bg-slate-800'}`}></div>

          <div className={`flex items-center space-x-2 ${currentStep >= 3 ? 'text-amber-400' : 'text-slate-500'}`}>
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold ${
              currentStep === 3 ? 'bg-amber-500 text-slate-950' : 'bg-slate-800 text-slate-400'
            }`}>
              3
            </span>
            <span className="hidden sm:inline">Security</span>
          </div>
        </div>

        {/* Form Card */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-500 via-amber-400 to-amber-600"></div>

          {error && (
            <div className="mb-5 p-3.5 rounded-lg bg-red-950/50 border border-red-500/40 flex items-start space-x-2.5 text-red-200 text-xs">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-400" />
              <p className="font-medium">{error}</p>
            </div>
          )}

          {/* STEP 1: Company Profile */}
          {currentStep === 1 && (
            <form onSubmit={handleStep1Submit} className="space-y-4">
              <div className="border-b border-slate-800 pb-3 mb-4">
                <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider font-mono">
                  Step 1: Organization Identification
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Enter legal entity details. Official domain email is required.
                </p>
              </div>

              {/* Company Name */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Organization / Company Name
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Building2 className="h-4 w-4" />
                  </div>
                  <input
                    type="text"
                    name="organizationName"
                    value={formData.organizationName}
                    onChange={handleChange}
                    placeholder="e.g. Apex Industrial Dynamics"
                    required
                    className="block w-full pl-10 pr-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/80"
                  />
                </div>
              </div>

              {/* Official Email */}
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
                    name="officialEmail"
                    value={formData.officialEmail}
                    onChange={handleChange}
                    placeholder="security@apex-industrial.com"
                    required
                    className="block w-full pl-10 pr-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/80 font-mono"
                  />
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Verification tokens and recovery dispatches will be sent here.
                </p>
              </div>

              {/* Industry Sector */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Industry Sector
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Briefcase className="h-4 w-4" />
                  </div>
                  <select
                    name="industry"
                    value={formData.industry}
                    onChange={handleChange}
                    required
                    className="block w-full pl-10 pr-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/80"
                  >
                    <option value="">Select industry classification...</option>
                    {industries.map((ind) => (
                      <option key={ind} value={ind}>
                        {ind}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Headquarters Location */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Operational Location / HQ
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <MapPin className="h-4 w-4" />
                  </div>
                  <input
                    type="text"
                    name="location"
                    value={formData.location}
                    onChange={handleChange}
                    placeholder="e.g. Austin, TX or Berlin, Germany"
                    required
                    className="block w-full pl-10 pr-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/80"
                  />
                </div>
              </div>

              {/* Next Button */}
              <div className="pt-3">
                <button
                  type="submit"
                  disabled={codeSending}
                  className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-amber-500/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  {codeSending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Dispatching Email Verification...</span>
                    </>
                  ) : (
                    <>
                      <span>Proceed to Verification</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </form>
          )}

          {/* STEP 2: Email Verification */}
          {currentStep === 2 && (
            <form onSubmit={handleStep2Submit} className="space-y-5">
              <div className="border-b border-slate-800 pb-3 mb-2">
                <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider font-mono">
                  Step 2: Email Verification
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Enter the 6-digit confirmation code dispatched to{' '}
                  <span className="text-amber-400 font-mono font-medium">{formData.officialEmail}</span>.
                </p>
              </div>

              {/* Mock dev code hint banner for easy testing */}
              {devCodeHint && (
                <div className="p-3 bg-amber-950/30 border border-amber-500/40 rounded-lg text-xs font-mono text-amber-300">
                  <span className="font-bold">[DEVELOPMENT DISPATCH LOG]</span> Verification code:
                  <button
                    type="button"
                    onClick={() => setFormData((p) => ({ ...p, verificationCode: devCodeHint }))}
                    className="ml-2 px-2 py-0.5 rounded bg-amber-500 text-slate-950 font-bold hover:bg-amber-400 transition-colors"
                  >
                    Auto-Fill {devCodeHint}
                  </button>
                </div>
              )}

              {/* 6-Digit Code Input */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 text-center">
                  Enter 6-Digit Verification Code
                </label>
                <div className="flex justify-center">
                  <input
                    type="text"
                    name="verificationCode"
                    maxLength="6"
                    value={formData.verificationCode}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        verificationCode: e.target.value.replace(/\D/g, ''),
                      }))
                    }
                    placeholder="000000"
                    autoFocus
                    required
                    className="w-48 py-3 text-center bg-slate-950 border-2 border-slate-800 focus:border-amber-500 rounded-xl text-2xl font-mono tracking-[0.5em] text-amber-400 focus:outline-none focus:ring-4 focus:ring-amber-500/20"
                  />
                </div>
              </div>

              <div className="text-center">
                <button
                  type="button"
                  onClick={handleResendCode}
                  disabled={codeSending}
                  className="text-xs text-amber-400 hover:text-amber-300 font-mono inline-flex items-center space-x-1.5 cursor-pointer disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Resend Verification Code</span>
                </button>
              </div>

              {/* Nav buttons */}
              <div className="flex space-x-3 pt-3">
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="w-1/3 flex items-center justify-center space-x-1.5 py-3 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs uppercase tracking-wider transition-colors cursor-pointer"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back</span>
                </button>
                <button
                  type="submit"
                  className="w-2/3 flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-amber-500/20 transition-all cursor-pointer"
                >
                  <span>Verify & Set Password</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </form>
          )}

          {/* STEP 3: Password & Security */}
          {currentStep === 3 && (
            <form onSubmit={handleStep3Submit} className="space-y-4">
              <div className="border-b border-slate-800 pb-3 mb-2">
                <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider font-mono">
                  Step 3: Security & Master Password
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Establish an industrial-strength passphrase for organizational administrative control.
                </p>
              </div>

              {/* Create Password */}
              <div>
                <PasswordInput
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  autoComplete="new-password"
                  label="Create Master Password"
                  placeholder="Create high-entropy password"
                />
                <PasswordStrengthIndicator password={formData.password} />
              </div>

              {/* Confirm Password */}
              <div className="pt-1">
                <PasswordInput
                  id="confirmPassword"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  required
                  autoComplete="new-password"
                  label="Confirm Master Password"
                  placeholder="Repeat master password"
                  error={
                    formData.confirmPassword && formData.password !== formData.confirmPassword
                      ? 'Passwords do not match'
                      : ''
                  }
                />
              </div>

              {/* Nav buttons */}
              <div className="flex space-x-3 pt-3">
                <button
                  type="button"
                  onClick={() => setCurrentStep(2)}
                  className="w-1/3 flex items-center justify-center space-x-1.5 py-3 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs uppercase tracking-wider transition-colors cursor-pointer"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back</span>
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-2/3 flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-amber-500/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Provisioning Organization...</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-4 h-4" />
                      <span>Complete Registration</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}

          {/* Already have an ID? */}
          <div className="mt-6 pt-5 border-t border-slate-800/80 text-center">
            <p className="text-xs text-slate-400">
              Already possess an Organization Registration ID?{' '}
              <Link to="/login" className="text-amber-400 hover:text-amber-300 font-semibold">
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
