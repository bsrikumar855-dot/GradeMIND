"use client";

import * as React from "react";
import { Menu, Search, Bell, ShieldCheck, User } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface NavbarProps {
  onMenuClick?: () => void;
  onSearchClick?: () => void;
  onLogout?: () => void;
  userDisplayName?: string;
  userRole?: string;
}

export const Navbar: React.FC<NavbarProps> = ({
  onMenuClick,
  onSearchClick,
  userDisplayName = "Academic Administrator",
  userRole = "Faculty Lead",
}) => {
  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b-2 border-emerald-800/20 bg-white/95 backdrop-blur-md px-6 md:px-8 transition-all shadow-2xs">
      
      {/* Left: Search Bar & Mobile Menu */}
      <div className="flex items-center gap-4">
        {onMenuClick && (
          <Button variant="ghost" size="sm" onClick={onMenuClick} className="md:hidden h-10 w-10 p-0 text-black hover:bg-emerald-100 rounded-xl group">
            <Menu className="h-5 w-5 group-hover:scale-110 transition-transform duration-300" />
          </Button>
        )}
        
        {/* Quick Search Bar */}
        <button 
          onClick={onSearchClick}
          className="hidden md:flex items-center gap-2.5 px-4 py-2 bg-emerald-50/70 hover:bg-emerald-100/90 border-2 border-emerald-400/80 rounded-2xl w-80 text-black text-sm transition-all text-left group shadow-2xs"
        >
          <Search className="w-4 h-4 text-[#183B25] group-hover:text-[#4A8B40] group-hover:scale-110 group-hover:rotate-6 transition-all duration-300 shrink-0" />
          <span className="text-xs text-black font-extrabold flex-1">Quick search or command...</span>
        </button>
      </div>

      {/* Right Action Icons & Profile Capsule */}
      <div className="flex items-center gap-4">
        
        {/* Notifications Icon with Hover Rotation */}
        <button className="relative p-2.5 rounded-xl text-black hover:bg-emerald-100/80 transition-colors border border-transparent hover:border-emerald-300 group">
          <Bell className="w-5 h-5 text-black group-hover:rotate-12 group-hover:scale-110 transition-transform duration-300" />
          <span className="absolute top-2 right-2 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-white animate-pulse"></span>
        </button>

        {/* User Profile Capsule */}
        <div className="flex items-center gap-3 p-1.5 pr-3 rounded-2xl bg-emerald-50/80 border-2 border-emerald-300/90 shadow-2xs group hover:border-emerald-500/80 transition-colors">
          <div className="relative w-9 h-9 rounded-xl bg-[#183B25] text-white flex items-center justify-center font-black text-xs shadow-xs border-2 border-[#4A8B40] shrink-0 overflow-hidden group-hover:scale-105 transition-transform duration-300">
            <img 
              src="/images/admin-avatar.png" 
              alt="Academic Administrator Avatar" 
              className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
            />
          </div>
          <div className="hidden lg:block text-left">
            <h4 className="text-xs font-black text-black leading-tight flex items-center gap-1">
              {userDisplayName} <ShieldCheck className="w-3.5 h-3.5 text-emerald-700 inline animate-pulse" />
            </h4>
            <span className="text-[10px] font-black text-emerald-900 block">{userRole}</span>
          </div>
        </div>

      </div>
    </header>
  );
};
Navbar.displayName = "Navbar";
