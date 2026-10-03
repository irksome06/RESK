import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Building2,
  Mail,
  Briefcase,
  MapPin,
  ArrowRight,
  ArrowLeft,
  AlertTriangle,
  Send,
  Loader2,
  Zap,
} from 'lucide-react';
import { api } from '../services/api';
import PasswordInput from '../components/PasswordInput';
import PasswordStrengthIndicator from '../components/PasswordStrengthIndicator';
import AuthLayout from '../components/AuthLayout';

export default function RegisterPage() {
  const navigate = useNavigate();

  // Wizard state: 1: Details, 2: Verification, 3: Password Setup
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
    'Energy & Power Generation',
    'Heavy Industrial Manufacturing',
    'Chemical Processing & Refining',
    'Semiconductors & Cleanrooms',
    'Robotics & Discrete Automation',
    'Automotive & Heavy Transport',
    'Data Centers & Critical Infrastructure',
    'Cold Chain & Logistics Facilities',
    'Steel, Metals & Mining Operations',
    'Commercial Real Estate & Campuses',
    'Other Industrial Operations',
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
      setError('Headquarters or facility operational location is required.');
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
    <AuthLayout>
      <div className="w-full space-y-4">
        {/* Step Indicator */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-white border border-slate-200 rounded-xl font-mono text-xs shadow-2xs">
          <div className={`flex items-center space-x-2 ${currentStep >= 1 ? 'text-teal-800' : 'text-slate-400'}`}>
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold ${
                currentStep === 1
                  ? 'bg-teal-600 text-white'
                  : currentStep > 1
                  ? 'bg-teal-100 text-teal-800 border border-teal-300'
                  : 'bg-slate-100 text-slate-400'
              }`}
            >
              1
            </span>
            <span className="hidden sm:inline font-sans font-medium text-slate-700">Facility Profile</span>
          </div>

          <div className={`h-0.5 flex-1 mx-3 ${currentStep >= 2 ? 'bg-teal-400' : 'bg-slate-200'}`}></div>

          <div className={`flex items-center space-x-2 ${currentStep >= 2 ? 'text-teal-800' : 'text-slate-400'}`}>
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold ${
                currentStep === 2
                  ? 'bg-teal-600 text-white'
                  : currentStep > 2
                  ? 'bg-teal-100 text-teal-800 border border-teal-300'
                  : 'bg-slate-100 text-slate-400'
              }`}
            >
              2
            </span>
            <span className="hidden sm:inline font-sans font-medium text-slate-700">Verify Email</span>
          </div>

          <div className={`h-0.5 flex-1 mx-3 ${currentStep >= 3 ? 'bg-teal-400' : 'bg-slate-200'}`}></div>

          <div className={`flex items-center space-x-2 ${currentStep >= 3 ? 'text-teal-800' : 'text-slate-400'}`}>
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold ${
                currentStep === 3 ? 'bg-teal-600 text-white' : 'bg-slate-100 text-slate-400'
              }`}
            >
              3
            </span>
            <span className="hidden sm:inline font-sans font-medium text-slate-700">Password</span>
          </div>
        </div>

        {/* Main Registration Card */}
        <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-xl shadow-slate-200/50 relative overflow-hidden border border-slate-200">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-teal-600 via-amber-400 to-emerald-500"></div>

          {/* Heading and Subheading */}
          <div className="mb-5 space-y-1">
            <h2
              className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 uppercase"
              style={{ fontFamily: 'var(--font-display, sans-serif)' }}
            >
              SET UP YOUR ENERGY WORKSPACE
            </h2>
            <p className="text-xs sm:text-sm text-slate-600">
              Connect your organization to RESK Energy Intelligence
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3.5 rounded-xl bg-red-50 border border-red-200 flex items-start space-x-2.5 text-red-800 text-xs">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-600" />
              <p className="font-medium">{error}</p>
            </div>
          )}

          {/* STEP 1: Company Profile */}
          {currentStep === 1 && (
            <form onSubmit={handleStep1Submit} className="space-y-4">
              {/* Company Name */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  Organization / Company Name
                </label>
                <div className="relative rounded-lg shadow-2xs">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Building2 className="h-4 w-4 text-teal-600" />
                  </div>
                  <input
                    type="text"
                    name="organizationName"
                    value={formData.organizationName}
                    onChange={handleChange}
                    placeholder="e.g. Apex Industrial Dynamics"
                    required
                    className="block w-full pl-10 pr-4 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 transition-all"
                  />
                </div>
              </div>

              {/* Official Email */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  Official Company Email
                </label>
                <div className="relative rounded-lg shadow-2xs">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Mail className="h-4 w-4 text-teal-600" />
                  </div>
                  <input
                    type="email"
                    name="officialEmail"
                    value={formData.officialEmail}
                    onChange={handleChange}
                    placeholder="operations@apex-industrial.com"
                    required
                    className="block w-full pl-10 pr-4 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 font-mono transition-all"
                  />
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Verification code and energy alerts will be dispatched here.
                </p>
              </div>

              {/* Industry Sector */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  Industry Sector
                </label>
                <div className="relative rounded-lg shadow-2xs">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Briefcase className="h-4 w-4 text-teal-600" />
                  </div>
                  <select
                    name="industry"
                    value={formData.industry}
                    onChange={handleChange}
                    required
                    className="block w-full pl-10 pr-4 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 transition-all"
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

              {/* Operational Location */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  Operational Location / Facility HQ
                </label>
                <div className="relative rounded-lg shadow-2xs">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <MapPin className="h-4 w-4 text-teal-600" />
                  </div>
                  <input
                    type="text"
                    name="location"
                    value={formData.location}
                    onChange={handleChange}
                    placeholder="e.g. Austin, TX or Frankfurt, Germany"
                    required
                    className="block w-full pl-10 pr-4 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 transition-all"
                  />
                </div>
              </div>

              {/* Next Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={codeSending}
                  className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-md shadow-amber-400/25 transition-all cursor-pointer disabled:opacity-50"
                >
                  {codeSending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Dispatching Verification Code...</span>
                    </>
                  ) : (
                    <>
                      <span>Proceed to Email Verification</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </form>
          )}

          {/* STEP 2: Email Verification */}
          {currentStep === 2 && (
            <form onSubmit={handleStep2Submit} className="space-y-4">
              <div className="border-b border-slate-100 pb-3 mb-2">
                <span className="text-[11px] font-mono text-teal-700 uppercase tracking-wide font-medium">
                  Step 2 // Email Confirmation
                </span>
                <p className="text-xs text-slate-600 mt-1">
                  Enter the 6-digit confirmation code dispatched to{' '}
                  <span className="text-teal-800 font-mono font-semibold">{formData.officialEmail}</span>.
                </p>
              </div>

              {/* Development Code helper banner */}
              {devCodeHint && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs font-mono text-amber-900">
                  <span className="font-bold">[DEVELOPMENT SIMULATION]</span> Code:
                  <button
                    type="button"
                    onClick={() => setFormData((p) => ({ ...p, verificationCode: devCodeHint }))}
                    className="ml-2 px-2.5 py-0.5 rounded bg-amber-400 text-slate-950 font-bold hover:bg-amber-300 transition-colors shadow-2xs"
                  >
                    Auto-Fill {devCodeHint}
                  </button>
                </div>
              )}

              {/* 6-Digit Code Input */}
              <div className="py-2">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-2 text-center">
                  6-Digit Verification Code
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
                    className="w-48 py-3 text-center bg-white border-2 border-slate-300 focus:border-teal-600 rounded-xl text-2xl font-mono tracking-[0.5em] text-slate-900 focus:outline-none focus:ring-4 focus:ring-teal-500/15"
                  />
                </div>
              </div>

              <div className="text-center">
                <button
                  type="button"
                  onClick={handleResendCode}
                  disabled={codeSending}
                  className="text-xs text-teal-700 hover:text-teal-800 font-medium inline-flex items-center space-x-1.5 cursor-pointer disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Resend Verification Code</span>
                </button>
              </div>

              {/* Nav buttons */}
              <div className="flex space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="w-1/3 flex items-center justify-center space-x-1.5 py-3 px-3 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs uppercase tracking-wider transition-colors cursor-pointer"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back</span>
                </button>
                <button
                  type="submit"
                  className="w-2/3 flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-md shadow-amber-400/25 transition-all cursor-pointer"
                >
                  <span>Verify & Set Password</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </form>
          )}

          {/* STEP 3: Password Setup */}
          {currentStep === 3 && (
            <form onSubmit={handleStep3Submit} className="space-y-4">
              <div className="border-b border-slate-100 pb-3 mb-2">
                <span className="text-[11px] font-mono text-teal-700 uppercase tracking-wide font-medium">
                  Step 3 // Password Setup
                </span>
                <p className="text-xs text-slate-600 mt-1">
                  Create a secure password to protect your organization's energy workspace.
                </p>
              </div>

              {/* Password */}
              <div>
                <PasswordInput
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  autoComplete="new-password"
                  label="Password"
                  placeholder="Enter strong password"
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
                  label="Confirm Password"
                  placeholder="Repeat password"
                  error={
                    formData.confirmPassword && formData.password !== formData.confirmPassword
                      ? 'Passwords do not match'
                      : ''
                  }
                />
              </div>

              {/* Nav buttons */}
              <div className="flex space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(2)}
                  className="w-1/3 flex items-center justify-center space-x-1.5 py-3 px-3 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs uppercase tracking-wider transition-colors cursor-pointer"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back</span>
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-2/3 flex items-center justify-center space-x-2 py-3 px-4 rounded-lg bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-md shadow-amber-400/25 transition-all cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Creating Workspace...</span>
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4" />
                      <span>Complete Setup</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}

          {/* Already have an ID? */}
          <div className="mt-5 pt-4 border-t border-slate-100 text-center">
            <p className="text-xs text-slate-600">
              Already possess an Organization Registration ID?{' '}
              <Link to="/login" className="text-teal-700 hover:text-teal-800 font-semibold">
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </div>
    </AuthLayout>
  );
}
