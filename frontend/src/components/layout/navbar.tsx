"use client";

import * as React from "react";
import { Menu, Sparkles, Search, Bell, ShieldCheck, Cpu } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface NavbarProps {
  onMenuClick?: () => void;
  onLogout?: () => void;
  userDisplayName?: string;
  userRole?: string;
}

export const Navbar: React.FC<NavbarProps> = ({
  onMenuClick,
  userDisplayName = "Academic Administrator",
  userRole = "Faculty Lead",
}) => {
  return (
    <header className="sticky top-0 z-30 flex h-20 w-full items-center justify-between border-b border-slate-200/60 bg-white/80 backdrop-blur-xl px-6 md:px-10 transition-all">
      <div className="flex items-center gap-4">
        {onMenuClick && (
          <Button variant="ghost" size="sm" onClick={onMenuClick} className="md:hidden h-10 w-10 p-0 text-slate-500 hover:bg-slate-100 rounded-xl">
            <Menu className="h-5 w-5" />
          </Button>
        )}
        
        {/* Quick Search Bar */}
        <div className="hidden md:flex items-center gap-2 px-4 py-2 bg-slate-100/80 hover:bg-slate-100 border border-slate-200/60 rounded-xl w-72 text-slate-400 text-sm transition-all focus-within:w-80 focus-within:border-emerald-500 focus-within:bg-white focus-within:ring-2 focus-within:ring-emerald-500/20">
          <Search className="w-4 h-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search exams, students, roll nos..."
            className="bg-transparent border-0 outline-none text-slate-800 text-xs w-full placeholder:text-slate-400"
          />
          <kbd className="px-1.5 py-0.5 text-[10px] font-bold text-slate-400 bg-white border border-slate-200 rounded">⌘K</kbd>
        </div>
      </div>

      {/* Right Action Icons & Profile */}
      <div className="flex items-center gap-4">
        {/* Model Status Pill */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-semibold shadow-sm">
          <Cpu className="w-3.5 h-3.5 text-emerald-600 animate-pulse" />
          <span>Groq 120B & Gemini Active</span>
        </div>

        {/* Notifications Button */}
        <button className="relative p-2.5 rounded-xl text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-white"></span>
        </button>

        {/* User Profile Capsule */}
        <div className="flex items-center gap-3 pl-3 border-l border-slate-200/80">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-slate-900 to-slate-700 text-white flex items-center justify-center font-bold text-sm shadow-md shadow-slate-900/10">
            {userDisplayName.split(' ').map(n => n[0]).join('').substring(0, 2)}
          </div>
          <div className="hidden lg:block text-left">
            <h4 className="text-xs font-bold text-slate-900 leading-tight flex items-center gap-1">
              {userDisplayName} <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 inline" />
            </h4>
            <span className="text-[10px] font-semibold text-slate-400">{userRole}</span>
          </div>
        </div>
      </div>
    </header>
  );
};
Navbar.displayName = "Navbar";
