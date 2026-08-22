'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Lock, Mail, User, ShieldCheck, ArrowRight, Sparkles } from 'lucide-react';
import { AuthService } from '@/services/auth.service';

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('teacher');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setInfo('');
    setIsSubmitting(true);

    try {
      if (mode === 'register') {
        await AuthService.register(name, email, role, password);
        setInfo('Account created successfully. You can now sign in.');
        setMode('login');
        setPassword('');
        setIsSubmitting(false);
        return;
      }

      await AuthService.login(email, password);
      window.location.href = '/dashboard';
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.response?.data?.message || err?.message;
      setError(detail || `${mode === 'login' ? 'Login' : 'Registration'} failed. Please try again.`);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full grid grid-cols-1 lg:grid-cols-2 bg-[#EBF3E8] text-left overflow-hidden">
      
      {/* Left Pane - Soft Sage Branding (Matching Image 1 with prominent greens & double color logo text) */}
      <div className="p-8 md:p-16 flex flex-col justify-between bg-[#EBF3E8] relative overflow-hidden">
        
        {/* Top Header Logo - Double-Color Logo Text */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#183B25] flex items-center justify-center shadow-md overflow-hidden border-2 border-[#183B25]">
            <img src="/images/logo.png" alt="GradeMIND Logo" className="w-full h-full object-cover" />
          </div>
          <span className="text-2xl font-black font-serif tracking-tight flex items-center">
            <span className="text-[#183B25]">Grade</span>
            <span className="text-[#4A8B40]">MIND</span>
          </span>
        </div>

        {/* Hero Title & Illustration */}
        <div className="my-auto py-12 max-w-lg space-y-6">
          <h1 className="text-4xl md:text-5xl font-serif font-extrabold text-black leading-[1.15] tracking-tight">
            Empower your grading with <span className="text-[#4A8B40] font-normal italic">AI Assistance.</span>
          </h1>
          <p className="text-sm font-bold text-black leading-relaxed max-w-md">
            Upload answer sheets, let the AI analyze, and generate comprehensive reports in seconds.
          </p>

          {/* Central Hero Illustration Card */}
          <div className="relative mt-8 bg-white rounded-2xl p-6 shadow-md border-2 border-emerald-800/30 max-w-md flex flex-col items-center">
            <img 
              src="/images/login-illustration.png" 
              alt="Grading Illustration" 
              className="w-full h-56 object-contain"
              onError={(e) => {
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
            <div className="flex items-center gap-2 mt-4 px-4 py-1.5 rounded-full bg-emerald-100 border border-emerald-400 text-black text-xs font-black">
              <Sparkles className="w-4 h-4 text-[#183B25]" /> Autonomous OCR & Value Point Scorer
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="text-xs text-black font-bold">
          © 2026 GradeMIND Inc. All rights reserved.
        </div>
      </div>

      {/* Right Pane - Dark Forest Green with White Form Card & Black Text */}
      <div className="bg-[#183B25] p-6 md:p-12 flex items-center justify-center relative">
        
        {/* Centered White Card */}
        <div className="w-full max-w-md bg-white rounded-3xl p-8 md:p-10 shadow-2xl space-y-6 text-left border-2 border-emerald-700/40">
          
          <div className="space-y-1">
            <h2 className="text-2xl font-serif font-black text-black tracking-tight">
              {mode === 'login' ? 'Welcome Back' : 'Create Account'}
            </h2>
            <p className="text-xs text-black font-bold">
              {mode === 'login' ? 'Please enter your details to sign in.' : 'Enter your academic information to register.'}
            </p>
          </div>

          {/* Mode Switcher */}
          <div className="grid grid-cols-2 gap-1 p-1 bg-emerald-100 rounded-xl border border-emerald-300">
            <button
              type="button"
              onClick={() => setMode('login')}
              className={`py-1.5 text-xs font-black rounded-lg transition-all ${
                mode === 'login' ? 'bg-[#183B25] text-white shadow-xs' : 'text-black hover:text-[#183B25]'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => setMode('register')}
              className={`py-1.5 text-xs font-black rounded-lg transition-all ${
                mode === 'register' ? 'bg-[#183B25] text-white shadow-xs' : 'text-black hover:text-[#183B25]'
              }`}
            >
              Register
            </button>
          </div>

          {error && (
            <div className="p-3 bg-rose-50 border border-rose-300 text-rose-800 rounded-xl text-xs font-black">
              {error}
            </div>
          )}
          {info && (
            <div className="p-3 bg-emerald-50 border border-emerald-300 text-black rounded-xl text-xs font-black">
              {info}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div className="space-y-1">
                <label className="text-xs font-black text-black uppercase tracking-wider block">Full Name</label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Prof. Jane Doe"
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-bold text-black placeholder:text-slate-500 focus:outline-none focus:border-[#4A8B40] focus:ring-1 focus:ring-[#4A8B40]"
                  />
                </div>
              </div>
            )}

            <div className="space-y-1">
              <label className="text-xs font-black text-black uppercase tracking-wider block">Email</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="teacher@school.edu"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-bold text-black placeholder:text-slate-500 focus:outline-none focus:border-[#4A8B40] focus:ring-1 focus:ring-[#4A8B40]"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-black text-black uppercase tracking-wider block">Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-bold text-black placeholder:text-slate-500 focus:outline-none focus:border-[#4A8B40] focus:ring-1 focus:ring-[#4A8B40]"
                />
              </div>
            </div>

            {mode === 'register' && (
              <div className="space-y-1">
                <label className="text-xs font-black text-black uppercase tracking-wider block">Role</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-bold text-black focus:outline-none focus:border-[#4A8B40]"
                >
                  <option value="teacher">Faculty Member / Professor</option>
                  <option value="admin">Exam Administrator</option>
                  <option value="evaluator">Teaching Assistant</option>
                </select>
              </div>
            )}

            {mode === 'login' && (
              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center gap-2 cursor-pointer text-black font-bold">
                  <input type="checkbox" className="rounded border-slate-300 text-[#4A8B40] focus:ring-[#4A8B40]" />
                  Remember me
                </label>
                <a href="#" className="text-[#183B25] hover:text-[#4A8B40] font-black">
                  Forgot password?
                </a>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 bg-[#4A8B40] hover:bg-[#3B7233] text-white font-black text-sm rounded-xl transition-all shadow-md flex items-center justify-center gap-2 mt-4"
            >
              {isSubmitting ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  {mode === 'login' ? 'Sign In' : 'Create Account'} <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="text-center text-xs text-black font-bold pt-2 border-t border-slate-200">
            Don&apos;t have an account? <button onClick={() => setMode('register')} className="text-[#183B25] font-black hover:underline">Request access</button>
          </div>

        </div>

      </div>

    </div>
  );
}
