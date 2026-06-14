"use client";

import * as React from "react";
import { Sidebar } from "./sidebar";
import { Navbar } from "./navbar";
import { useAuth } from "@/store/auth-context";

export interface DashboardLayoutProps {
  children: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(false);
  const { user, logout } = useAuth();

  const toggleSidebar = () => setIsSidebarOpen((prev) => !prev);
  const closeSidebar = () => setIsSidebarOpen(false);

  return (
    <div className="min-h-screen bg-brand-background flex">
      {/* Sidebar - Desktop is fixed, Mobile uses toggle */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={closeSidebar}
        onLogout={logout}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col md:pl-64 min-h-screen">
        {/* Navbar */}
        <Navbar
          onMenuClick={toggleSidebar}
          onLogout={logout}
          userDisplayName={user?.name || "Teacher"}
          userRole={user?.role || "Educator"}
        />

        {/* Page Content Body */}
        <main className="flex-1 flex flex-col overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

DashboardLayout.displayName = "DashboardLayout";
