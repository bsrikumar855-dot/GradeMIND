"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "./sidebar";
import { Navbar } from "./navbar";
import { CommandMenu } from "@/components/ui/command-menu";
import { useAuth } from "@/store/auth-context";

export interface DashboardLayoutProps {
  children: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(false);
  const [isCommandOpen, setIsCommandOpen] = React.useState(false);
  const { user, logout } = useAuth();

  const toggleSidebar = () => setIsSidebarOpen((prev) => !prev);
  const closeSidebar = () => setIsSidebarOpen(false);

  // Global Ctrl+K / Cmd+K listener
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsCommandOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const currentUser = user || { name: "Academic Administrator", role: "Faculty Lead" };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar - Desktop fixed w-72 */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={closeSidebar}
        onLogout={logout}
      />

      {/* Command Palette Modal */}
      <CommandMenu
        isOpen={isCommandOpen}
        onClose={() => setIsCommandOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col md:pl-72 min-h-screen">
        {/* Navbar */}
        <Navbar
          onMenuClick={toggleSidebar}
          onSearchClick={() => setIsCommandOpen(true)}
          onLogout={logout}
          userDisplayName={currentUser.name}
          userRole={currentUser.role}
        />
        {/* Page Content Body */}
        <main className="flex-1 p-6 md:p-10 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

DashboardLayout.displayName = "DashboardLayout";
