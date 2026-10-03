import React, { useState } from 'react';
import { Eye, EyeOff, Lock } from 'lucide-react';

export default function PasswordInput({
  id,
  name,
  value,
  onChange,
  placeholder = '••••••••••••',
  required = false,
  autoComplete = 'current-password',
  label = 'Password',
  error,
}) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={id} className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
          {label}
        </label>
      )}
      <div className="relative rounded-lg shadow-2xs">
        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
          <Lock className="h-4 w-4" />
        </div>
        <input
          type={showPassword ? 'text' : 'password'}
          id={id}
          name={name}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          autoComplete={autoComplete}
          className={`block w-full pl-10 pr-10 py-2.5 bg-white border rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 transition-all ${
            error
              ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
              : 'border-slate-300 focus:border-teal-600 hover:border-slate-400'
          }`}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-teal-700 transition-colors focus:outline-none cursor-pointer"
          tabIndex="-1"
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      {error && <p className="mt-1.5 text-xs text-red-600 font-medium">{error}</p>}
    </div>
  );
}
