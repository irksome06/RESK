import React from 'react';
import { Check, X } from 'lucide-react';

export default function PasswordStrengthIndicator({ password = '' }) {
  const criteria = [
    { label: 'At least 8 characters', met: password.length >= 8 },
    { label: 'One uppercase letter (A-Z)', met: /[A-Z]/.test(password) },
    { label: 'One lowercase letter (a-z)', met: /[a-z]/.test(password) },
    { label: 'One numeric digit (0-9)', met: /[0-9]/.test(password) },
    { label: 'One special symbol (!@#$%^&*)', met: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password) },
  ];

  const metCount = criteria.filter((c) => c.met).length;

  const getStrengthMeta = () => {
    if (metCount === 0) return { label: 'Empty', color: 'bg-slate-700', text: 'text-slate-500', width: '0%' };
    if (metCount <= 2) return { label: 'Weak', color: 'bg-red-500', text: 'text-red-400', width: '25%' };
    if (metCount <= 4) return { label: 'Moderate', color: 'bg-amber-500', text: 'text-amber-400', width: '70%' };
    return { label: 'Industrial Grade', color: 'bg-emerald-500', text: 'text-emerald-400', width: '100%' };
  };

  const meta = getStrengthMeta();

  return (
    <div className="mt-2.5 p-3 rounded-lg bg-slate-900/60 border border-slate-800/80">
      <div className="flex items-center justify-between text-xs mb-1.5">
        <span className="text-slate-400 font-mono text-[11px] uppercase tracking-wider">Complexity Level</span>
        <span className={`font-mono font-semibold text-[11px] ${meta.text}`}>{meta.label}</span>
      </div>

      {/* Progress Bar */}
      <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden mb-2.5">
        <div
          className={`h-full transition-all duration-300 ease-out ${meta.color}`}
          style={{ width: meta.width }}
        />
      </div>

      {/* Criteria Checklist */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[11px]">
        {criteria.map((item, index) => (
          <div
            key={index}
            className={`flex items-center space-x-1.5 transition-colors ${
              item.met ? 'text-emerald-400' : 'text-slate-500'
            }`}
          >
            {item.met ? (
              <Check className="w-3.5 h-3.5 flex-shrink-0 text-emerald-400" />
            ) : (
              <X className="w-3.5 h-3.5 flex-shrink-0 text-slate-600" />
            )}
            <span className={item.met ? 'text-slate-300 font-medium' : 'text-slate-500'}>
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
