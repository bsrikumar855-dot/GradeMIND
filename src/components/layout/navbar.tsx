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
  return (
    <header className="sticky top-0 z-30 flex h-24 w-full items-center justify-between border-b border-gray-100 bg-white/60 backdrop-blur-md px-8 xl:px-10">
      <div className="flex items-center gap-6">
        {onMenuClick && (
          <Button variant="ghost" size="sm" onClick={onMenuClick} className="md:hidden h-12 w-12 p-0 text-gray-500">
            <Menu className="h-7 w-7" />
          </Button>
        )}
        <div className="flex items-center gap-3 md:hidden">
          <div className="w-12 h-12 rounded-xl bg-brand-primary flex items-center justify-center">
            <span className="text-white font-bold text-3xl leading-none">G</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-6">
        <button className="p-3 rounded-full hover:bg-gray-50 text-gray-400 transition-colors relative">
          <span className="absolute top-2 right-2 w-3 h-3 bg-red-500 rounded-full border border-white"></span>
          <Bell className="h-7 w-7" />
        </button>
        <div className="h-12 w-px bg-gray-100" />
        <div className="flex items-center gap-4">
          <div className="hidden flex-col text-right md:flex">
            <span className="text-lg font-bold text-brand-dark">{userDisplayName}</span>
            <span className="text-xs text-gray-500 font-semibold uppercase tracking-wider">{userRole}</span>
          </div>
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-surface text-brand-dark text-lg font-bold">
            JD
          </div>
          {onLogout && (
            <Button variant="ghost" size="sm" onClick={onLogout} className="h-12 w-12 p-0 text-gray-400 hover:text-red-600 ml-2">
              <LogOut className="h-6 w-6" />
            </Button>
          )}
        </div>
      </div>
    </header>
  );
};
Navbar.displayName = "Navbar";
