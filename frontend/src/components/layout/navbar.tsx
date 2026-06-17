"use client";

import * as React from "react";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GradeMindLogo } from "@/components/brand";

export interface NavbarProps {
  onMenuClick?: () => void;
  onLogout?: () => void;
  userDisplayName?: string;
  userRole?: string;
}

export const Navbar: React.FC<NavbarProps> = ({
  onMenuClick,
  onLogout,
  userDisplayName,
  userRole,
}) => {
  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-gray-100 bg-white/50 backdrop-blur-md px-6">
      <div className="flex items-center gap-4">
        {onMenuClick && (
          <Button variant="ghost" size="sm" onClick={onMenuClick} className="md:hidden h-9 w-9 p-0 text-gray-500">
            <Menu className="h-5 w-5" />
          </Button>
        )}
        <div className="flex items-center gap-2 md:hidden">
          <GradeMindLogo variant="navbar" showText={false} size={32} />
        </div>
      </div>
      <div />
    </header>
  );
};
Navbar.displayName = "Navbar";
