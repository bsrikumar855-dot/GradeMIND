'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/store/auth-context';

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading: authLoading, error: authError, clearError } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setLocalError(null);
    clearError();

    try {
      await login(email, password);
      // On success, redirect to dashboard
      router.push('/dashboard');
    } catch (err: unknown) {
      // Extract error message from axios response
      let errorMessage = "Login failed. Please check your credentials.";
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: { detail?: string; message?: string } } };
        errorMessage = axiosError.response?.data?.detail
          || axiosError.response?.data?.message
          || errorMessage;
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      setLocalError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const displayError = localError || authError;
  const loading = isLoading || authLoading;

  return (
    <div className="min-h-screen flex items-center justify-center p-6 lg:p-12 relative overflow-hidden bg-brand-background">
      
      {/* Full Page Background Illustration */}
      <div className="absolute inset-0 w-full h-full z-0 pointer-events-none opacity-60">
        <Image 
          src="/images/login-illustration.png" 
          alt="Background Illustration" 
          fill
          className="object-cover object-center mix-blend-multiply scale-[1.1]"
          priority
        />
      </div>

      {/* Subtle floating blobs for depth */}
      <div className="absolute -top-20 -right-20 w-[600px] h-[600px] bg-[#86B77B]/10 rounded-full blur-3xl animate-pulse pointer-events-none z-0" />
      <div className="absolute -bottom-24 -left-24 w-[800px] h-[800px] bg-[#5B8DEF]/[0.05] rounded-full blur-3xl animate-pulse pointer-events-none z-0" style={{ animationDelay: '2s' }} />

      <div className="relative z-10 w-full max-w-7xl mx-auto flex flex-col lg:flex-row items-center justify-between gap-12">
        
        {/* Left Side - Branding */}
        <div className="w-full lg:w-1/2 flex flex-col justify-center bg-white/40 backdrop-blur-md p-10 rounded-3xl border border-white/50 shadow-xl">
          <div className="flex items-center gap-2 mb-12">
            <div className="w-10 h-10 rounded-xl bg-brand-primary flex items-center justify-center shadow-lg">
              <span className="text-white font-bold text-2xl leading-none">G</span>
            </div>
            <span className="text-4xl font-extrabold text-black tracking-tight drop-shadow-sm">GradeMIND</span>
          </div>
          
          <h1 className="text-5xl xl:text-6xl font-extrabold text-black mb-6 leading-tight drop-shadow-md">
            Empower your grading <br/>
            with <span className="text-brand-primary drop-shadow-sm">AI Assistance</span>.
          </h1>
          <p className="text-black/80 font-semibold text-xl xl:text-2xl max-w-lg leading-relaxed drop-shadow-sm">
            Upload answer sheets, let the AI analyze, and generate comprehensive reports in seconds.
          </p>
        </div>

        {/* Right Side - Login Form */}
        <div className="w-full lg:w-[500px] relative z-10">
          <div className="bg-white rounded-[28px] p-12 sm:p-16 shadow-[0_20px_60px_rgba(0,0,0,0.3)] border border-white/80">
            <div className="mb-10 text-center">
              <h2 className="text-4xl font-extrabold text-brand-dark mb-3">Welcome Back</h2>
              <p className="text-gray-500 text-lg font-medium">Please enter your details to sign in.</p>
            </div>

            {/* Error Display */}
            {displayError && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
                <p className="text-red-600 text-sm font-medium">{displayError}</p>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-8">
              <div className="space-y-2">
                <label className="text-lg font-semibold text-brand-dark block" htmlFor="email">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-5 py-4.5 rounded-xl bg-gray-50 border border-gray-200 focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/20 outline-none transition-all text-brand-dark placeholder-gray-400 text-xl"
                  placeholder="teacher@school.edu"
                />
              </div>

              <div className="space-y-2">
                <label className="text-lg font-semibold text-brand-dark block" htmlFor="password">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-5 py-4.5 rounded-xl bg-gray-50 border border-gray-200 focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/20 outline-none transition-all text-brand-dark placeholder-gray-400 text-xl"
                  placeholder="••••••••"
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer group">
                  <div className="relative flex items-center justify-center">
                    <input type="checkbox" className="peer w-5 h-5 rounded border-gray-300 text-brand-primary focus:ring-brand-primary appearance-none border checked:bg-brand-primary checked:border-brand-primary transition-all" />
                    <svg className="absolute w-3 h-3 text-white opacity-0 peer-checked:opacity-100 pointer-events-none transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span className="text-lg text-gray-500 group-hover:text-brand-dark transition-colors">Remember me</span>
                </label>
                <button type="button" className="text-lg font-medium text-brand-primary hover:text-brand-dark transition-colors">
                  Forgot password?
                </button>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-brand-primary text-white font-semibold py-5 px-4 rounded-xl text-xl hover:bg-opacity-90 active:scale-[0.98] transition-all duration-200 disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-[0_10px_30px_rgba(134,183,123,0.3)] mt-6"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Signing in...
                  </>
                ) : (
                  'Sign In'
                )}
              </button>
            </form>

            <div className="mt-12 text-center">
              <p className="text-lg text-gray-500">
                Don&apos;t have an account?{' '}
                <button type="button" className="text-brand-primary font-bold hover:text-brand-dark transition-colors">
                  Request access
                </button>
              </p>
            </div>
        </div>
      </div>
      </div>
    </div>
  );
}
