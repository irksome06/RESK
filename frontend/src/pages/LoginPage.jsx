import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  Building2,
  Lock,
  Eye,
  EyeOff,
  Mail,
  Briefcase,
  MapPin,
  ArrowRight,
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  Zap,
  Wrench,
  Layers,
  Moon,
  Leaf,
  BarChart3,
  CloudRain,
  Calendar,
  Clock,
  Target,
  Coins,
  TrendingUp,
  Loader2,
  Copy,
  Check,
  Send,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import ReskLogo from '../components/ReskLogo';
import PasswordStrengthIndicator from '../components/PasswordStrengthIndicator';

export default function LoginPage({ initialMode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  // Mode: 'login' or 'register' (matches route or props)
  const isRegisterRoute = initialMode === 'register' || location.pathname === '/register';
  const [mode, setMode] = useState(isRegisterRoute ? 'register' : 'login');

  useEffect(() => {
    if (location.pathname === '/register') {
      setMode('register');
    } else if (location.pathname === '/login') {
      setMode('login');
    }
  }, [location.pathname]);

  const switchMode = (newMode) => {
    setMode(newMode);
    setError('');
    const newPath = newMode === 'register' ? '/register' : '/login';
    window.history.pushState(null, '', newPath);
  };

  // Login Form State
  const initialRegId = location.state?.registration_id || '';
  const successNotice = location.state?.message || '';

  const [registrationId, setRegistrationId] = useState(initialRegId);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Registration Form State
  const [regStep, setRegStep] = useState(1); // 1: Details, 2: Verification, 3: Password, 4: Success
  const [regForm, setRegForm] = useState({
    organizationName: '',
    officialEmail: '',
    industry: '',
    location: '',
    verificationCode: '',
    password: '',
    confirmPassword: '',
  });
  const [showRegPassword, setShowRegPassword] = useState(false);
  const [showRegConfirmPassword, setShowRegConfirmPassword] = useState(false);
  const [codeSending, setCodeSending] = useState(false);
  const [devCodeHint, setDevCodeHint] = useState('');
  const [createdRegId, setCreatedRegId] = useState('');
  const [copiedId, setCopiedId] = useState(false);

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

  // Carousel State & Swipe Handling
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState(0);
  const startXRef = useRef(0);
  const currentDragRef = useRef(0);

  const slides = [
    {
      id: 1,
      number: '01 / 04',
      title: 'Energy Optimization',
      description:
        'Monitor consumption, detect inefficiencies and get actionable insights to reduce energy costs across all industrial lines.',
      image:
        'https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?auto=format&fit=crop&w=1800&q=80',
      objectPosition: 'center 35%',
      icon: Zap,
      hasOverlayBadge: false,
      benefits: [
        { icon: Leaf, value: '-18%', label: 'Energy Cost' },
        { icon: BarChart3, value: '+12%', label: 'Efficiency' },
        { icon: CloudRain, value: '-22%', label: 'CO₂ Emissions' },
      ],
    },
    {
      id: 2,
      number: '02 / 04',
      title: 'Maintenance Scheduling',
      description:
        'Predict equipment issues, plan ahead, and keep heavy machinery running at peak thermodynamic performance.',
      image:
        'https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1800&q=80',
      objectPosition: 'center 25%',
      icon: Wrench,
      hasOverlayBadge: false,
      benefits: [
        { icon: Calendar, value: '-30%', label: 'Downtime' },
        { icon: CheckCircle2, value: '+25%', label: 'Equipment Life' },
        { icon: Clock, value: '-40%', label: 'Breakdowns' },
      ],
    },
    {
      id: 3,
      number: '03 / 04',
      title: 'Priority Settlement',
      description:
        'Use machine intelligence to rank operational priorities, balance grid power resources, and maximize production output.',
      image:
        'https://images.unsplash.com/photo-1581092795360-fd1ca04f0952?auto=format&fit=crop&w=1800&q=80',
      objectPosition: 'center 25%',
      icon: Layers,
      hasOverlayBadge: false,
      benefits: [
        { icon: Target, value: '+20%', label: 'On-time Delivery' },
        { icon: Coins, value: '-15%', label: 'Operational Cost' },
        { icon: TrendingUp, value: '+10%', label: 'Productivity' },
      ],
    },
    {
      id: 4,
      number: '04 / 04',
      title: 'Machine Sleep Mode',
      description:
        'Automatically eliminate idle power draw during off-peak windows and optimize demand response tariffs.',
      image:
        'https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?auto=format&fit=crop&w=1800&q=80',
      objectPosition: 'center 40%',
      icon: Moon,
      hasOverlayBadge: true,
      overlayText: 'Sleep Mode Active',
      benefits: [
        { icon: Zap, value: '-25%', label: 'Idle Consumption' },
        { icon: Leaf, value: '+8%', label: 'Energy Savings' },
        { icon: CheckCircle2, value: '+12%', label: 'Sustainability' },
      ],
    },
  ];

  // Auto-play feature carousel every 5.5 seconds, pauses on interaction
  useEffect(() => {
    if (isHovered || isDragging) return;
    const interval = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % slides.length);
    }, 5500);
    return () => clearInterval(interval);
  }, [isHovered, isDragging, slides.length]);

  // Swipe / Drag gesture handlers
  const handlePointerDown = (clientX) => {
    setIsDragging(true);
    startXRef.current = clientX;
    currentDragRef.current = 0;
    setDragOffset(0);
  };

  const handlePointerMove = (clientX) => {
    if (!isDragging) return;
    const deltaX = clientX - startXRef.current;
    currentDragRef.current = deltaX;
    setDragOffset(deltaX);
  };

  const handlePointerUp = () => {
    if (!isDragging) return;
    setIsDragging(false);
    const deltaX = currentDragRef.current;
    if (deltaX < -50) {
      setCurrentSlide((prev) => (prev + 1) % slides.length);
    } else if (deltaX > 50) {
      setCurrentSlide((prev) => (prev === 0 ? slides.length - 1 : prev - 1));
    }
    setDragOffset(0);
  };

  // Attach global listeners while dragging so fast gestures or leaving bounds don't freeze the drag
  useEffect(() => {
    if (!isDragging) return;
    const onWindowMove = (e) => handlePointerMove(e.clientX);
    const onWindowUp = () => handlePointerUp();
    window.addEventListener('mousemove', onWindowMove);
    window.addEventListener('mouseup', onWindowUp);
    return () => {
      window.removeEventListener('mousemove', onWindowMove);
      window.removeEventListener('mouseup', onWindowUp);
    };
  }, [isDragging]);

  // LOGIN SUBMIT
  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const cleanId = registrationId.trim().toUpperCase();
    if (!cleanId) {
      setError('Please enter your Organization Registration ID (e.g. RESK-7F42K9).');
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

  // REGISTER STEP 1 SUBMIT
  const handleRegStep1Submit = async (e) => {
    e.preventDefault();
    setError('');

    if (!regForm.organizationName.trim()) {
      setError('Organization name is required.');
      return;
    }
    if (!regForm.officialEmail.trim() || !regForm.officialEmail.includes('@')) {
      setError('A valid official company email is required.');
      return;
    }
    if (!regForm.industry) {
      setError('Please select an industry sector.');
      return;
    }
    if (!regForm.location.trim()) {
      setError('Headquarters or operational facility location is required.');
      return;
    }

    setCodeSending(true);
    try {
      const resp = await api.sendVerificationCode(regForm.officialEmail);
      if (resp.dev_token) {
        setDevCodeHint(resp.dev_token);
      }
      setRegStep(2);
    } catch (err) {
      setError(err.message || 'Failed to dispatch email verification code. Please check the address.');
    } finally {
      setCodeSending(false);
    }
  };

  // REGISTER STEP 2 (Verify Code)
  const handleRegStep2Submit = async (e) => {
    e.preventDefault();
    setError('');
    const cleanCode = regForm.verificationCode.trim();
    if (!cleanCode || cleanCode.length < 6) {
      setError('Please enter the 6-digit verification code sent to your official email.');
      return;
    }
    setRegStep(3);
  };

  const handleResendCode = async () => {
    setError('');
    setCodeSending(true);
    try {
      const resp = await api.sendVerificationCode(regForm.officialEmail);
      if (resp.dev_token) {
        setDevCodeHint(resp.dev_token);
      }
    } catch (err) {
      setError(err.message || 'Failed to resend verification code.');
    } finally {
      setCodeSending(false);
    }
  };

  // REGISTER STEP 3 (Set Password & Complete)
  const handleRegStep3Submit = async (e) => {
    e.preventDefault();
    setError('');

    if (regForm.password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (regForm.password !== regForm.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        organization_name: regForm.organizationName.trim(),
        official_email: regForm.officialEmail.trim(),
        industry: regForm.industry,
        location: regForm.location.trim(),
        password: regForm.password,
        confirm_password: regForm.confirmPassword,
        verification_code: regForm.verificationCode.trim(),
      };

      const result = await api.register(payload);
      setCreatedRegId(result.registration_id);
      setRegStep(4);
    } catch (err) {
      setError(err.message || 'Registration failed. Please review your details.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyRegistrationId = () => {
    if (createdRegId) {
      navigator.clipboard.writeText(createdRegId);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  const handleProceedToLoginWithId = () => {
    setRegistrationId(createdRegId);
    setPassword('');
    switchMode('login');
  };

  const currentSlideData = slides[currentSlide];
  const SlideIcon = currentSlideData.icon;

  return (
    <div className="w-full min-h-screen lg:h-screen bg-[#F8FAFC] flex flex-col justify-between overflow-x-hidden lg:overflow-hidden px-4 sm:px-6 lg:px-8 py-2.5 lg:py-3 relative select-none">
      {/* Decorative Energy-Flow Curved Lines (Top-Right) */}
      <svg
        className="absolute top-0 right-0 w-[480px] h-[300px] pointer-events-none opacity-35 z-0"
        viewBox="0 0 480 300"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path d="M80 0C180 100 320 110 480 50" stroke="#14B8A6" strokeWidth="1.75" strokeDasharray="4 4" />
        <path d="M0 50C190 140 360 150 480 100" stroke="#F59E0B" strokeWidth="1.5" />
        <path d="M140 0C260 180 380 200 480 180" stroke="#10B981" strokeWidth="1" opacity="0.6" />
      </svg>

      {/* Decorative Energy-Flow Curved Lines (Bottom-Left) */}
      <svg
        className="absolute bottom-0 left-0 w-[500px] h-[240px] pointer-events-none opacity-35 z-0"
        viewBox="0 0 500 240"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path d="M0 180C160 120 320 160 500 240" stroke="#14B8A6" strokeWidth="1.5" />
        <path d="M0 220C180 150 350 180 500 210" stroke="#F59E0B" strokeWidth="1.75" />
      </svg>

      {/* TOP HEADER - Full Width */}
      <header className="relative z-10 w-full flex items-center justify-between pb-1 flex-shrink-0">
        <div className="flex items-center space-x-3">
          <ReskLogo className="w-8 h-8" />
          <div className="flex items-center space-x-2">
            <span
              className="text-2xl font-bold tracking-tight text-slate-900"
              style={{ fontFamily: 'var(--font-display, sans-serif)' }}
            >
              RESK
            </span>
            <span className="text-slate-300 font-light mx-1">|</span>
            <span className="text-sm font-medium text-slate-500 hidden sm:inline">
              Energy Intelligence Platform
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-2.5 text-xs text-slate-600 font-mono">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="font-semibold text-slate-700">System Online</span>
          <span className="text-slate-300 font-light">|</span>
          <span className="text-slate-500">v1.0</span>
        </div>
      </header>

      {/* MAIN VIEWPORT-FILL CONTAINER (Left ~71% Carousel, Right ~29% Auth Card) */}
      <main className="relative z-10 flex-1 w-full min-h-0 flex flex-col lg:flex-row gap-4 lg:gap-5 my-1">
        
        {/* LEFT SECTION (~69% on Desktop): LARGE SLIDING FEATURE CAROUSEL WITH SWIPE & DRAG */}
        <div
          className="lg:w-[68%] xl:w-[69%] flex flex-col h-full min-h-0"
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => {
            setIsHovered(false);
            if (isDragging) handlePointerUp();
          }}
        >
          {/* Main Showcase Slide Card (Fills available height) */}
          <div className="flex-1 flex flex-col bg-white rounded-3xl border border-slate-200/90 shadow-xl shadow-slate-200/50 overflow-hidden relative min-h-0">
            {/* HERO Real Industrial Photo: Enlarged downwards (~76% of carousel height) */}
            <div
              className="h-[76%] w-full relative overflow-hidden bg-slate-900 rounded-t-3xl flex-shrink-0 cursor-grab active:cursor-grabbing select-none"
              onMouseDown={(e) => handlePointerDown(e.clientX)}
              onTouchStart={(e) => handlePointerDown(e.touches[0].clientX)}
            >
              {/* Sliding Track */}
              <div
                className="flex h-full"
                style={{
                  transform: `translateX(calc(-${currentSlide * 100}% + ${dragOffset}px))`,
                  transition: isDragging ? 'none' : 'transform 500ms cubic-bezier(0.4, 0, 0.2, 1)',
                }}
              >
                {slides.map((slide, idx) => (
                  <div key={slide.id} className="min-w-full h-full relative flex-shrink-0">
                    <img
                      src={slide.image}
                      alt={slide.title}
                      className="w-full h-full object-cover select-none pointer-events-none"
                      style={{ objectPosition: slide.objectPosition || 'center center' }}
                      loading={idx === 0 ? 'eager' : 'lazy'}
                      draggable={false}
                    />
                    {/* Vignette */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/30"></div>

                    {/* Top-Left: Enlarged Slide Number Badge */}
                    <div className="absolute top-5 left-5 px-4 py-1.5 rounded-full bg-black/55 backdrop-blur-md border border-white/25 text-white text-sm font-mono font-bold tracking-widest shadow-lg">
                      {slide.number}
                    </div>

                    {/* Top-Right: Enlarged Machine Sleep Mode Badge (Slide 4) */}
                    {slide.hasOverlayBadge && (
                      <div className="absolute top-5 right-5 px-4 py-2 rounded-full bg-slate-900/90 backdrop-blur-md border border-emerald-500/50 text-emerald-400 text-sm font-bold flex items-center space-x-2 shadow-xl animate-pulse">
                        <Moon className="w-4 h-4 text-emerald-400 fill-emerald-400/20" />
                        <span>{slide.overlayText}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Slide Information Area: Occupies ~24% with enlarged text & zero blank space */}
            <div className="h-[24%] px-6 lg:px-8 py-2.5 lg:py-3 flex flex-col justify-between bg-white min-h-0 border-t border-slate-100">
              <div>
                <div className="flex items-center space-x-3">
                  <div className="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center shadow-xs flex-shrink-0">
                    <SlideIcon className="w-5 h-5" />
                  </div>
                  <h2 className="text-xl sm:text-2xl font-extrabold tracking-tight text-slate-900 leading-tight">
                    {currentSlideData.title}
                  </h2>
                </div>

                <p className="text-sm sm:text-base text-slate-600 font-medium leading-normal max-w-4xl mt-1 line-clamp-1">
                  {currentSlideData.description}
                </p>
              </div>

              {/* 3 Benefit Indicators directly beneath description in one full horizontal row */}
              <div className="grid grid-cols-3 gap-3 pt-2 border-t border-slate-100">
                {currentSlideData.benefits.map((b, idx) => {
                  const BIcon = b.icon;
                  return (
                    <div
                      key={idx}
                      className="flex items-center space-x-3 px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-100 shadow-2xs"
                    >
                      <BIcon className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                      <div className="flex flex-col min-w-0">
                        <span className="font-black text-base sm:text-lg text-emerald-700 tracking-tight leading-none">
                          {b.value}
                        </span>
                        <span className="text-xs sm:text-sm text-slate-600 truncate font-semibold mt-0.5">
                          {b.label}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Carousel Bottom Progress Indicators (Dots only - NO arrow buttons) */}
          <div className="flex items-center justify-center space-x-2 pt-2 pb-0.5 flex-shrink-0">
            {slides.map((_, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setCurrentSlide(idx)}
                aria-label={`Go to slide ${idx + 1}`}
                className={`h-2 rounded-full transition-all duration-300 cursor-pointer ${
                  currentSlide === idx ? 'w-7 bg-teal-600' : 'w-2 bg-slate-300 hover:bg-slate-400'
                }`}
              />
            ))}
          </div>
        </div>

        {/* RIGHT SECTION (~31% on Desktop): UNIFIED DYNAMIC AUTHENTICATION PANEL (LOGIN & REGISTER) */}
        <div className="lg:w-[32%] xl:w-[31%] flex flex-col justify-center h-full min-h-0">
          <div className="bg-white rounded-3xl border border-slate-200/90 shadow-xl shadow-slate-200/60 p-6 sm:p-7 lg:p-8 flex flex-col justify-between h-full min-h-0 overflow-y-auto relative">
            
            {/* Top Brand Header */}
            <div className="flex-shrink-0">
              <div className="flex items-center space-x-3">
                <ReskLogo className="w-9 h-9" />
                <div>
                  <span
                    className="text-2xl font-bold tracking-tight text-slate-900 block leading-tight"
                    style={{ fontFamily: 'var(--font-display, sans-serif)' }}
                  >
                    RESK
                  </span>
                  <span className="text-xs font-medium text-slate-400 block -mt-0.5">
                    Energy Intelligence Platform
                  </span>
                </div>
              </div>

              {/* Title & Subtitle based on Mode */}
              {mode === 'login' ? (
                <div className="mt-4 sm:mt-5 mb-2 sm:mb-3">
                  <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
                    Welcome Back
                  </h1>
                  <p className="text-sm text-slate-500 mt-1">
                    Access your energy intelligence workspace
                  </p>
                </div>
              ) : (
                <div className="mt-4 sm:mt-5 mb-2 sm:mb-3">
                  <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
                    Set Up Your Energy Workspace
                  </h1>
                  <p className="text-sm text-slate-500 mt-1">
                    Connect your organization to RESK Energy Intelligence
                  </p>
                </div>
              )}

              {/* Success Notice from Registration Redirect */}
              {successNotice && mode === 'login' && (
                <div className="mb-3 p-3 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start space-x-2.5 text-emerald-800 text-xs sm:text-sm">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5 text-emerald-600" />
                  <div>
                    <p className="font-semibold">{successNotice}</p>
                    <p className="text-emerald-700 mt-0.5">
                      Please sign in with your Registration ID and password.
                    </p>
                  </div>
                </div>
              )}

              {/* Error Banner */}
              {error && (
                <div className="mb-3 p-3 rounded-xl bg-red-50 border border-red-200 flex items-start space-x-2.5 text-red-800 text-xs sm:text-sm">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-600" />
                  <p className="font-medium">{error}</p>
                </div>
              )}
            </div>

            {/* Middle Section (Form & Interaction) - Vertically Balanced to eliminate blank gap */}
            <div className="flex-1 flex flex-col justify-center my-auto py-1 min-h-0">
              {/* ============================================================ */}
              {/* MODE A: LOGIN FORM */}
              {/* ============================================================ */}
              {mode === 'login' && (
                <form onSubmit={handleLoginSubmit} className="space-y-4">
                  {/* Organization ID */}
                  <div>
                    <label
                      htmlFor="registrationId"
                      className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      ORGANIZATION ID
                    </label>
                    <div className="relative rounded-xl shadow-xs">
                      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                        <Building2 className="h-5 w-5" />
                      </div>
                      <input
                        id="registrationId"
                        name="registrationId"
                        type="text"
                        value={registrationId}
                        onChange={(e) => setRegistrationId(e.target.value.toUpperCase())}
                        placeholder="e.g. RESK-12345"
                        required
                        autoFocus
                        className="block w-full pl-11 pr-4 py-3 sm:py-3.5 bg-slate-50/50 focus:bg-white border border-slate-300 rounded-xl text-base text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 font-mono tracking-wider transition-all"
                      />
                    </div>
                  </div>

                  {/* Password */}
                  <div>
                    <label
                      htmlFor="password"
                      className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      PASSWORD
                    </label>
                    <div className="relative rounded-xl shadow-xs">
                      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                        <Lock className="h-5 w-5" />
                      </div>
                      <input
                        id="password"
                        name="password"
                        type={showPassword ? 'text' : 'password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Enter your password"
                        required
                        autoComplete="current-password"
                        className="block w-full pl-11 pr-11 py-3 sm:py-3.5 bg-slate-50/50 focus:bg-white border border-slate-300 rounded-xl text-base text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 transition-all"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-teal-700 transition-colors cursor-pointer"
                        tabIndex="-1"
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                      >
                        {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                      </button>
                    </div>
                  </div>

                  {/* Remember Me & Forgot Password */}
                  <div className="flex items-center justify-between text-sm pt-0.5">
                    <label className="flex items-center space-x-2 cursor-pointer select-none text-slate-600 hover:text-slate-800 font-medium">
                      <input
                        type="checkbox"
                        checked={rememberMe}
                        onChange={(e) => setRememberMe(e.target.checked)}
                        className="w-4 h-4 rounded bg-white border-slate-300 text-teal-600 focus:ring-teal-500/30"
                      />
                      <span>Remember me</span>
                    </label>

                    <Link
                      to="/forgot-password"
                      className="text-teal-700 hover:text-teal-800 font-semibold transition-colors"
                    >
                      Forgot password?
                    </Link>
                  </div>

                  {/* Sign In CTA Button */}
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full flex items-center justify-center space-x-2 py-3.5 sm:py-4 px-5 rounded-xl bg-[#F5B515] hover:bg-[#E5A80E] text-slate-950 font-bold text-sm uppercase tracking-wider shadow-md hover:shadow-lg shadow-amber-400/25 transition-all cursor-pointer disabled:opacity-50 mt-2"
                  >
                    {isSubmitting ? (
                      <span>SIGNING IN...</span>
                    ) : (
                      <>
                        <span>SIGN IN</span>
                        <ArrowRight className="w-4.5 h-4.5 text-slate-950" />
                      </>
                    )}
                  </button>
                </form>
              )}

              {/* ============================================================ */}
              {/* MODE B: REGISTRATION FLOW (Integrated in same card) */}
              {/* ============================================================ */}
              {mode === 'register' && (
                <div>
                  {/* Step 1: Organization Profile */}
                  {regStep === 1 && (
                    <form onSubmit={handleRegStep1Submit} className="space-y-3">
                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                          Organization / Company Name
                        </label>
                        <div className="relative rounded-xl shadow-xs">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                            <Building2 className="h-4.5 w-4.5" />
                          </div>
                          <input
                            type="text"
                            value={regForm.organizationName}
                            onChange={(e) => setRegForm({ ...regForm, organizationName: e.target.value })}
                            placeholder="e.g. Apex Industrial Dynamics"
                            required
                            className="block w-full pl-10 pr-3 py-2.5 sm:py-3 bg-slate-50/50 focus:bg-white border border-slate-300 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                          Official Company Email
                        </label>
                        <div className="relative rounded-xl shadow-xs">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                            <Mail className="h-4.5 w-4.5" />
                          </div>
                          <input
                            type="email"
                            value={regForm.officialEmail}
                            onChange={(e) => setRegForm({ ...regForm, officialEmail: e.target.value })}
                            placeholder="operations@apex-industrial.com"
                            required
                            className="block w-full pl-10 pr-3 py-2.5 sm:py-3 bg-slate-50/50 focus:bg-white border border-slate-300 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 font-mono"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                          Industry Sector
                        </label>
                        <div className="relative rounded-xl shadow-xs">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                            <Briefcase className="h-4.5 w-4.5" />
                          </div>
                          <select
                            value={regForm.industry}
                            onChange={(e) => setRegForm({ ...regForm, industry: e.target.value })}
                            required
                            className="block w-full pl-10 pr-3 py-2.5 sm:py-3 bg-slate-50/50 focus:bg-white border border-slate-300 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600"
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

                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                          Operational Location / HQ
                        </label>
                        <div className="relative rounded-xl shadow-xs">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                            <MapPin className="h-4.5 w-4.5" />
                          </div>
                          <input
                            type="text"
                            value={regForm.location}
                            onChange={(e) => setRegForm({ ...regForm, location: e.target.value })}
                            placeholder="e.g. Austin, TX or Frankfurt, Germany"
                            required
                            className="block w-full pl-10 pr-3 py-2.5 sm:py-3 bg-slate-50/50 focus:bg-white border border-slate-300 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600"
                          />
                        </div>
                      </div>

                      <button
                        type="submit"
                        disabled={codeSending}
                        className="w-full flex items-center justify-center space-x-2 py-3.5 sm:py-4 px-5 rounded-xl bg-[#F5B515] hover:bg-[#E5A80E] text-slate-950 font-bold text-sm uppercase tracking-wider shadow-md hover:shadow-lg shadow-amber-400/25 transition-all cursor-pointer disabled:opacity-50 mt-2"
                      >
                        {codeSending ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>SENDING VERIFICATION...</span>
                          </>
                        ) : (
                          <>
                            <span>CONTINUE TO VERIFICATION</span>
                            <ArrowRight className="w-4.5 h-4.5 text-slate-950" />
                          </>
                        )}
                      </button>
                    </form>
                  )}

                  {/* Step 2: Verification Code */}
                  {regStep === 2 && (
                    <form onSubmit={handleRegStep2Submit} className="space-y-3.5">
                      <p className="text-sm text-slate-600">
                        Enter the 6-digit confirmation code dispatched to{' '}
                        <span className="font-semibold text-teal-800">{regForm.officialEmail}</span>.
                      </p>

                      {devCodeHint && (
                        <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-xl text-xs font-mono text-amber-900 flex items-center justify-between">
                          <span>Code: {devCodeHint}</span>
                          <button
                            type="button"
                            onClick={() => setRegForm({ ...regForm, verificationCode: devCodeHint })}
                            className="px-2 py-1 rounded bg-amber-400 text-slate-950 font-bold text-xs"
                          >
                            Auto-Fill
                          </button>
                        </div>
                      )}

                      <div className="flex justify-center py-2">
                        <input
                          type="text"
                          maxLength="6"
                          value={regForm.verificationCode}
                          onChange={(e) =>
                            setRegForm({
                              ...regForm,
                              verificationCode: e.target.value.replace(/\D/g, ''),
                            })
                          }
                          placeholder="000000"
                          autoFocus
                          required
                          className="w-48 py-3 text-center bg-white border-2 border-slate-300 focus:border-teal-600 rounded-xl text-2xl font-mono tracking-[0.4em] text-slate-900 focus:outline-none focus:ring-4 focus:ring-teal-500/15"
                        />
                      </div>

                      <div className="text-center">
                        <button
                          type="button"
                          onClick={handleResendCode}
                          disabled={codeSending}
                          className="text-xs text-teal-700 hover:text-teal-800 font-semibold inline-flex items-center space-x-1"
                        >
                          <Send className="w-3.5 h-3.5" />
                          <span>Resend verification code</span>
                        </button>
                      </div>

                      <div className="flex space-x-2 pt-1">
                        <button
                          type="button"
                          onClick={() => setRegStep(1)}
                          className="w-1/3 py-3 px-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs sm:text-sm transition-colors"
                        >
                          Back
                        </button>
                        <button
                          type="submit"
                          className="w-2/3 flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-[#F5B515] hover:bg-[#E5A80E] text-slate-950 font-bold text-xs sm:text-sm uppercase tracking-wider shadow-md"
                        >
                          <span>VERIFY & NEXT</span>
                          <ArrowRight className="w-4 h-4" />
                        </button>
                      </div>
                    </form>
                  )}

                  {/* Step 3: Password Setup */}
                  {regStep === 3 && (
                    <form onSubmit={handleRegStep3Submit} className="space-y-3.5">
                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                          Create Password
                        </label>
                        <div className="relative rounded-xl shadow-xs">
                          <input
                            type={showRegPassword ? 'text' : 'password'}
                            value={regForm.password}
                            onChange={(e) => setRegForm({ ...regForm, password: e.target.value })}
                            placeholder="Enter secure password"
                            required
                            className="block w-full px-3.5 py-3 bg-white border border-slate-300 rounded-xl text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600"
                          />
                          <button
                            type="button"
                            onClick={() => setShowRegPassword(!showRegPassword)}
                            className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400"
                          >
                            {showRegPassword ? <EyeOff className="h-4.5 w-4.5" /> : <Eye className="h-4.5 w-4.5" />}
                          </button>
                        </div>
                        <PasswordStrengthIndicator password={regForm.password} />
                      </div>

                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                          Confirm Password
                        </label>
                        <div className="relative rounded-xl shadow-xs">
                          <input
                            type={showRegConfirmPassword ? 'text' : 'password'}
                            value={regForm.confirmPassword}
                            onChange={(e) => setRegForm({ ...regForm, confirmPassword: e.target.value })}
                            placeholder="Repeat password"
                            required
                            className="block w-full px-3.5 py-3 bg-white border border-slate-300 rounded-xl text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600"
                          />
                          <button
                            type="button"
                            onClick={() => setShowRegConfirmPassword(!showRegConfirmPassword)}
                            className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400"
                          >
                            {showRegConfirmPassword ? <EyeOff className="h-4.5 w-4.5" /> : <Eye className="h-4.5 w-4.5" />}
                          </button>
                        </div>
                      </div>

                      <div className="flex space-x-2 pt-1">
                        <button
                          type="button"
                          onClick={() => setRegStep(2)}
                          className="w-1/3 py-3 px-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs sm:text-sm transition-colors"
                        >
                          Back
                        </button>
                        <button
                          type="submit"
                          disabled={isSubmitting}
                          className="w-2/3 flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-[#F5B515] hover:bg-[#E5A80E] text-slate-950 font-bold text-xs sm:text-sm uppercase tracking-wider shadow-md disabled:opacity-50"
                        >
                          {isSubmitting ? (
                            <span>INITIALIZING...</span>
                          ) : (
                            <>
                              <span>COMPLETE SETUP</span>
                              <ArrowRight className="w-4 h-4" />
                            </>
                          )}
                        </button>
                      </div>
                    </form>
                  )}

                  {/* Step 4: Success View */}
                  {regStep === 4 && (
                    <div className="space-y-4 py-2 text-center">
                      <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center mx-auto">
                        <CheckCircle2 className="w-7 h-7" />
                      </div>
                      <div>
                        <h3 className="text-lg font-bold text-slate-900">Workspace Initialized</h3>
                        <p className="text-sm text-slate-500 mt-1">
                          Use your Registration ID to access the platform.
                        </p>
                      </div>

                      <div className="p-3.5 bg-teal-50/70 border border-teal-200 rounded-xl">
                        <span className="text-[11px] font-mono text-teal-800 uppercase block mb-1">
                          Assigned Registration ID
                        </span>
                        <div className="font-mono text-2xl font-bold text-slate-900 tracking-wider">
                          {createdRegId}
                        </div>
                        <button
                          type="button"
                          onClick={handleCopyRegistrationId}
                          className="mt-2 text-xs font-mono text-teal-700 hover:text-teal-800 inline-flex items-center space-x-1"
                        >
                          {copiedId ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                              <span className="text-emerald-700 font-bold">COPIED!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" />
                              <span>Copy ID</span>
                            </>
                          )}
                        </button>
                      </div>

                      <button
                        type="button"
                        onClick={handleProceedToLoginWithId}
                        className="w-full py-3.5 px-4 rounded-xl bg-[#F5B515] hover:bg-[#E5A80E] text-slate-950 font-bold text-sm uppercase tracking-wider shadow-md"
                      >
                        SIGN IN WITH {createdRegId} →
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Mode Switch Prompt */}
              {mode === 'login' ? (
                <div className="mt-3.5 text-center sm:text-left text-sm">
                  <span className="text-slate-600">New organization? </span>
                  <button
                    type="button"
                    onClick={() => switchMode('register')}
                    className="text-teal-700 hover:text-teal-800 font-bold inline-flex items-center space-x-1 cursor-pointer hover:underline"
                  >
                    <span>Register your facility →</span>
                  </button>
                </div>
              ) : (
                <div className="mt-3.5 text-center sm:text-left text-sm">
                  <span className="text-slate-600">Already have an Organization ID? </span>
                  <button
                    type="button"
                    onClick={() => switchMode('login')}
                    className="text-teal-700 hover:text-teal-800 font-bold inline-flex items-center space-x-1 cursor-pointer hover:underline"
                  >
                    <span>Sign In →</span>
                  </button>
                </div>
              )}
            </div>

            {/* Bottom Eco-Callout Card with Factory/Turbine Silhouette */}
            <div className="flex-shrink-0 mt-3 pt-2 border-t border-slate-100">
              <div className="p-3.5 rounded-2xl bg-[#F0FDF4] border border-emerald-100 flex items-center justify-between gap-3">
                <div className="flex items-center space-x-2.5">
                  <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center flex-shrink-0">
                    <Leaf className="w-4 h-4" />
                  </div>
                  <p className="text-xs sm:text-[13px] text-emerald-900 leading-snug font-medium">
                    Powering efficient industries with intelligent energy solutions.
                  </p>
                </div>

                {/* Industrial Silhouette Line Art */}
                <svg
                  className="w-14 h-8 text-emerald-600/40 flex-shrink-0 opacity-80"
                  viewBox="0 0 70 40"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M5 35H65" />
                  <path d="M10 35V20L20 28V15L30 22V35" />
                  <path d="M30 35V18H45V35" />
                  <circle cx="55" cy="15" r="2" />
                  <path d="M55 15V35" />
                  <path d="M50 12L55 15L58 10" />
                </svg>
              </div>
            </div>
          </div>
        </div>

      </main>

      {/* BOTTOM FOOTER SLOGAN */}
      <footer className="relative z-10 w-full pt-1 flex items-center justify-between text-xs text-slate-500 flex-shrink-0">
        <div className="flex items-center space-x-2">
          <Leaf className="w-4 h-4 text-emerald-600" />
          <span className="font-medium text-slate-600">Smarter Energy. Better Tomorrow.</span>
        </div>
        <div className="text-slate-400 text-[11px] font-mono hidden sm:inline">
          ISO 50001 OPTIMIZATION PLATFORM // REAL-TIME TELEMETRY
        </div>
      </footer>
    </div>
  );
}
