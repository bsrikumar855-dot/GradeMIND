"use client";

import * as React from "react";
import { Bell, Menu, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface NavbarProps {
  onMenuClick?: () => void;
  userDisplayName?: string;
  userRole?: string;
  onLogout?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onMenuClick,
  userDisplayName = "Dr. Jane Doe",
  userRole = "Grade Administrator",
  onLogout,
}) => {
  const initials = userDisplayName
    ? userDisplayName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'U';

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-gray-100 bg-white/50 backdrop-blur-md px-6">
      <div className="flex items-center gap-4">
        {onMenuClick && (
          <Button variant="ghost" size="sm" onClick={onMenuClick} className="md:hidden h-9 w-9 p-0 text-gray-500">
            <Menu className="h-5 w-5" />
          </Button>
        )}
        <div className="flex items-center gap-2 md:hidden">
          <div className="w-8 h-8 rounded-lg bg-brand-primary flex items-center justify-center">
            <span className="text-white font-bold text-xl leading-none">G</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <button className="p-2 rounded-full hover:bg-gray-50 text-gray-400 transition-colors relative">
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-white"></span>
          <Bell className="h-5 w-5" />
        </button>
        <div className="h-8 w-px bg-gray-100" />
        <div className="flex items-center gap-3">
          <div className="hidden flex-col text-right md:flex">
            <span className="text-sm font-semibold text-brand-dark">{userDisplayName}</span>
            <span className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">{userRole}</span>
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-surface text-brand-dark font-bold">
            {initials}
          </div>
          {onLogout && (
            <Button variant="ghost" size="sm" onClick={onLogout} className="h-8 w-8 p-0 text-gray-400 hover:text-red-600 ml-2">
              <LogOut className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </header>
  );
};
Navbar.displayName = "Navbar";
