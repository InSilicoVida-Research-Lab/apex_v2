import React, { useState } from 'react';
import { Eye, EyeOff, Sparkles, ShieldCheck, CheckCircle2, FileText } from 'lucide-react';

interface LoginViewProps {
  onLoginSuccess: () => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('curator@example.org');
  const [password, setPassword] = useState('••••••••••••');
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onLoginSuccess();
  };

  return (
    <div className="min-h-screen w-full flex bg-white text-slate-900 font-sans selection:bg-sky-500 selection:text-white">
      {/* ----------------- LEFT PANE: AUTH FORM ----------------- */}
      <div className="w-full lg:w-1/2 flex flex-col justify-between p-8 sm:p-14 lg:p-20 z-10 bg-white">
        {/* Brand Header */}
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-sky-600 to-sky-500 flex items-center justify-center shadow-sm shadow-sky-500/20">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-base tracking-tight text-slate-900 flex items-center gap-1.5">
            APEX PBPK
          </span>
          <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-sky-100 text-sky-800">
            Audit Suite
          </span>
        </div>

        {/* Form Container */}
        <div className="w-full max-w-sm mx-auto my-auto py-8">
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 mb-2">
            Log In
          </h2>
          <p className="text-xs text-slate-500 mb-6">
            Access your auditable PBPK extraction workspace
          </p>

          {/* Social Logins */}
          <div className="space-y-2.5 mb-6">
            <button
              type="button"
              onClick={onLoginSuccess}
              className="w-full flex items-center justify-center gap-2.5 py-2.5 px-4 rounded-lg bg-white hover:bg-sky-50/70 border border-slate-200 hover:border-sky-300 text-xs font-medium text-slate-700 transition shadow-2xs"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
              <span>Continue with Google</span>
            </button>

            <button
              type="button"
              onClick={onLoginSuccess}
              className="w-full flex items-center justify-center gap-2.5 py-2.5 px-4 rounded-lg bg-white hover:bg-sky-50/70 border border-slate-200 hover:border-sky-300 text-xs font-medium text-slate-700 transition shadow-2xs"
            >
              <svg className="w-4 h-4 fill-current text-slate-800" viewBox="0 0 24 24">
                <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
              <span>Continue with GitHub</span>
            </button>

            <button
              type="button"
              onClick={onLoginSuccess}
              className="w-full flex items-center justify-center gap-2.5 py-2.5 px-4 rounded-lg bg-white hover:bg-sky-50/70 border border-slate-200 hover:border-sky-300 text-xs font-medium text-slate-700 transition shadow-2xs"
            >
              <span className="w-4 h-4 rounded-full bg-[#a6ce39] text-[#2c3038] font-bold text-[10px] flex items-center justify-center leading-none">
                iD
              </span>
              <span>Continue with ORCID</span>
            </button>
          </div>

          {/* Divider */}
          <div className="relative flex items-center justify-center my-5">
            <div className="border-t border-slate-200 w-full" />
            <span className="bg-white px-3 text-[11px] text-slate-400 uppercase tracking-widest absolute">
              or
            </span>
          </div>

          {/* Email / Password Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-slate-700 mb-1.5 font-medium">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.org"
                required
                className="w-full bg-white border border-slate-200 rounded-lg px-3.5 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition font-sans shadow-2xs"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs text-slate-700 font-medium">Password</label>
                <a href="#forgot" className="text-[11px] text-sky-600 hover:text-sky-700 font-medium transition">
                  Forgot password?
                </a>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full bg-white border border-slate-200 rounded-lg px-3.5 py-2 pr-9 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition font-mono shadow-2xs"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition"
                >
                  {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 px-4 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs tracking-wide transition shadow-sm hover:shadow shadow-sky-600/20 mt-2"
            >
              Log in
            </button>
          </form>

          {/* Create Account link */}
          <p className="text-center text-xs text-slate-500 mt-5">
            New here?{' '}
            <button
              type="button"
              onClick={onLoginSuccess}
              className="text-sky-600 hover:text-sky-700 hover:underline font-semibold"
            >
              Create an account
            </button>
          </p>
        </div>

        {/* Footer */}
        <div className="flex items-center gap-3 text-[11px] text-slate-400">
          <a href="#terms" className="hover:text-slate-600 transition">Terms</a>
          <span>&bull;</span>
          <a href="#privacy" className="hover:text-slate-600 transition">Privacy</a>
          <span>&bull;</span>
          <a href="mailto:support@apex-pbpk.org" className="text-sky-600 hover:text-sky-700 font-medium transition">
            [contact email]
          </a>
        </div>
      </div>

      {/* ----------------- RIGHT PANE: BRANDING HERO ----------------- */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-center px-12 xl:px-20 relative overflow-hidden bg-gradient-to-br from-sky-50 via-blue-50/50 to-indigo-50/40 border-l border-sky-100">
        {/* Subtle background glow */}
        <div className="absolute top-1/4 -right-16 w-96 h-96 bg-sky-200/40 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-10 left-10 w-72 h-72 bg-blue-200/30 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-xl z-10 space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/90 border border-sky-200 text-[11px] text-sky-800 font-medium shadow-2xs">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-600 animate-pulse" />
            Deterministic Extraction & Verifiable Audit
          </div>

          <h1 className="text-4xl xl:text-5xl font-black text-slate-900 tracking-tight leading-[1.18]">
            Weigh the evidence{' '}
            <span className="text-sky-600">faster</span>
          </h1>

          <p className="text-base text-slate-600 font-normal leading-relaxed">
            Every claim, parameter, and equation traced directly to a verbatim quote, a page, and a document table.
          </p>

          <div className="pt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-3.5 rounded-xl bg-white/80 border border-sky-100 shadow-2xs">
              <div className="flex items-center gap-2 text-sky-700 font-semibold text-xs mb-1">
                <FileText className="w-3.5 h-3.5" />
                <span>Split-Screen Audit</span>
              </div>
              <p className="text-[11px] text-slate-500">
                Click any parameter to jump directly to its Markdown table row and verbatim text snippet.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-white/80 border border-sky-100 shadow-2xs">
              <div className="flex items-center gap-2 text-emerald-700 font-semibold text-xs mb-1">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Tan (2021) 36 Checklist</span>
              </div>
              <p className="text-[11px] text-slate-500">
                Automated regulatory compliance assessment across all 36 WHO/OECD criteria with provenance.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};


