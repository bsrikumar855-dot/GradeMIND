'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { GradeMindLogo } from '@/components/brand';
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
        setInfo('Account created. You can now sign in.');
        setMode('login');
        setPassword('');
        setIsSubmitting(false);
        return;
      }

      await AuthService.login(email, password);
      // Full navigation so AuthProvider re-mounts and picks up the new
      // session cookie (it only checks on mount).
      window.location.href = '/dashboard';
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.response?.data?.message || err?.message;
      setError(detail || `${mode === 'login' ? 'Login' : 'Registration'} failed. Please try again.`);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-brand-background flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <GradeMindLogo variant="full-color" textSize="lg" />
        </div>

        <div className="bg-white p-8 rounded-2xl shadow-[0_10px_40px_rgba(47,90,58,0.08)] border border-gray-50">
          <h1 className="text-2xl font-bold text-brand-dark mb-1">
            {mode === 'login' ? 'Sign in' : 'Create an account'}
          </h1>
          <p className="text-sm text-gray-500 mb-6">
            {mode === 'login'
              ? 'Sign in to grade and review submissions.'
              : 'Register as a teacher or admin to start grading.'}
          </p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-xl text-sm font-semibold">
              {error}
            </div>
          )}
          {info && (
            <div className="mb-4 p-3 bg-brand-surface/40 border border-brand-primary/20 text-brand-dark rounded-xl text-sm font-semibold">
              {info}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div className="space-y-2">
                <label className="text-xs font-semibold text-gray-500">Full name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Jane Doe"
                  className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-brand-primary text-brand-dark text-sm font-medium"
                />
              </div>
            )}

            <div className="space-y-2">
              <label className="text-xs font-semibold text-gray-500">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@school.edu"
                className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-brand-primary text-brand-dark text-sm font-medium"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-gray-500">Password</label>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-brand-primary text-brand-dark text-sm font-medium"
              />
            </div>

            {mode === 'register' && (
              <div className="space-y-2">
                <label className="text-xs font-semibold text-gray-500">Role</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-brand-primary text-brand-dark text-sm font-medium"
                >
                  <option value="teacher">Teacher</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full px-6 py-3.5 rounded-xl font-bold text-white bg-brand-primary hover:bg-opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 transition-all shadow-md flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : mode === 'login' ? (
                'Sign in'
              ) : (
                'Create account'
              )}
            </button>
          </form>

          <button
            type="button"
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login');
              setError('');
              setInfo('');
            }}
            className="w-full mt-5 text-sm font-semibold text-brand-primary hover:underline"
          >
            {mode === 'login' ? "Don't have an account? Register" : 'Already have an account? Sign in'}
          </button>
        </div>
      </div>
    </div>
  );
}
