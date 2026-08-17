"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "./sidebar";
import { Navbar } from "./navbar";
import { useAuth } from "@/store/auth-context";

export interface DashboardLayoutProps {
  children: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(false);
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();

  const toggleSidebar = () => setIsSidebarOpen((prev) => !prev);
  const closeSidebar = () => setIsSidebarOpen(false);

  // In local mode / demo mode, fallback gracefully if auth is disabled
  const currentUser = user || { name: "Academic Administrator", role: "Faculty Lead" };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar - Desktop is fixed w-72 */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={closeSidebar}
        onLogout={logout}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col md:pl-72 min-h-screen">
        {/* Navbar */}
        <Navbar
          onMenuClick={toggleSidebar}
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
