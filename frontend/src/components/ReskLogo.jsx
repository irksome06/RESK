import React from 'react';

export default function ReskLogo({ className = "w-8 h-8" }) {
  return (
    <svg className={className} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="reskTeal" x1="4" y1="4" x2="20" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0D9488" />
          <stop offset="100%" stopColor="#10B981" />
        </linearGradient>
        <linearGradient id="reskGold" x1="16" y1="4" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FBBF24" />
          <stop offset="100%" stopColor="#F59E0B" />
        </linearGradient>
      </defs>
      {/* Left Teal Leaf Component */}
      <path
        d="M18 3.5C11.5 3.5 5 9 4.2 16.8C3.5 24 8 30 14 32.5L19.5 19L11.5 19L20 4.2C19.3 3.7 18.7 3.5 18 3.5Z"
        fill="url(#reskTeal)"
      />
      {/* Right Gold Energy Component */}
      <path
        d="M18 3.5C24.5 3.5 31 9 31.8 16.8C32.5 24 28 30 22 32.5L16.5 19L24.5 19L16 4.2C16.7 3.7 17.3 3.5 18 3.5Z"
        fill="url(#reskGold)"
      />
    </svg>
  );
}
