"use client";

import * as React from "react";
import { Menu, Search, Bell, ShieldCheck, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

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
  userRole = "Faculty Examiner",
}) => {
  return (
    <header className="sticky top-0 z-30 flex h-14 w-full items-center justify-between border-b border-slate-200 bg-white/95 backdrop-blur-xs px-4 md:px-6 transition-all">
      <div className="flex items-center gap-3">
        {onMenuClick && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onMenuClick}
            className="md:hidden h-8 w-8 text-slate-600 hover:bg-slate-100"
          >
            <Menu className="h-4 w-4" />
          </Button>
        )}

        {/* Workspace / Context Indicator */}
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="font-mono text-[11px] text-slate-600 bg-slate-50">
            CBSE Board Exam 2026
          </Badge>
          <span className="text-slate-300 hidden sm:inline">/</span>
          <span className="text-xs font-semibold text-slate-700 hidden sm:inline">
            Evaluation OS Workspace
          </span>
        </div>
      </div>

      {/* Center: Command Palette Trigger */}
      <button
        onClick={onSearchClick}
        className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-md w-64 text-slate-400 text-xs transition-colors text-left group cursor-pointer"
      >
        <Search className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-700 transition-colors" />
        <span className="text-xs text-slate-500 font-medium flex-1">Search or command...</span>
        <kbd className="px-1.5 py-0.5 text-[10px] font-mono font-bold text-slate-500 bg-white border border-slate-200 rounded shadow-2xs">
          ⌘K
        </kbd>
      </button>

      {/* Right: Actions & User Profile */}
      <div className="flex items-center gap-3">
        {/* Notifications */}
        <button className="relative p-2 rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-teal-600"></span>
        </button>

        {/* User Capsule */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
          <div className="w-7 h-7 rounded-md bg-slate-900 text-white flex items-center justify-center font-mono font-bold text-xs">
            {userDisplayName
              .split(" ")
              .map((n) => n[0])
              .join("")
              .substring(0, 2)}
          </div>
          <div className="hidden lg:block text-left">
            <h4 className="text-xs font-bold text-slate-900 leading-none">
              {userDisplayName}
            </h4>
            <span className="text-[10px] text-slate-500 font-medium block mt-0.5">
              {userRole}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
Navbar.displayName = "Navbar";
