"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileCheck2,
  ListTodo,
  BarChart3,
  Users,
  FileText,
  Settings,
  HelpCircle,
  LogOut,
  X,
  BookOpen,
  ChevronRight,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/utils/cn";
import { Button } from "@/components/ui/button";

export interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
  onLogout?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen = true,
  onClose,
  onLogout,
}) => {
  const pathname = usePathname();

  const mainNavigation = [
    { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
    { name: "Assessments", href: "/upload", icon: BookOpen },
    { name: "Evaluation", href: "/evaluation", icon: FileCheck2 },
    { name: "Review Queue", href: "/review", icon: ListTodo },
    { name: "Students", href: "/student", icon: Users },
    { name: "Analytics", href: "/analytics", icon: BarChart3 },
    { name: "Reports", href: "/reports", icon: FileText },
  ];

  const systemNavigation = [
    { name: "Settings", href: "/settings", icon: Settings },
    { name: "Help & Docs", href: "/help", icon: HelpCircle },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/40 backdrop-blur-xs transition-opacity md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform duration-200 ease-in-out md:translate-x-0",
          isOpen ? "translate-x-0 shadow-xl" : "-translate-x-full"
        )}
      >
        {/* Brand & Institution Context */}
        <div className="flex h-16 items-center justify-between px-5 border-b border-slate-200/80">
          <Link href="/dashboard" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-md bg-slate-900 text-white flex items-center justify-center font-mono font-bold text-xs shadow-xs">
              GM
            </div>
            <div>
              <span className="text-sm font-bold tracking-tight text-slate-900 block leading-none">
                GradeMIND <span className="font-mono text-[10px] text-teal-600 font-bold ml-1">OS</span>
              </span>
              <span className="text-[10px] font-medium text-slate-500 block mt-0.5">
                Examination Platform
              </span>
            </div>
          </Link>
          {onClose && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="md:hidden h-8 w-8 text-slate-400 hover:text-slate-600"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 space-y-6 p-4 overflow-y-auto">
          {/* Main Module Section */}
          <div className="space-y-1">
            <div className="px-2 mb-2 text-metadata text-[10px] text-slate-400">
              Examination Modules
            </div>
            {mainNavigation.map((item) => {
              const Icon = item.icon;
              const isActive =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href));

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "group flex items-center justify-between rounded-md px-3 py-2 text-xs font-semibold transition-colors",
                    isActive
                      ? "bg-slate-900 text-white shadow-2xs"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  )}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon
                      className={cn(
                        "h-4 w-4 shrink-0 transition-colors",
                        isActive ? "text-teal-400" : "text-slate-400 group-hover:text-slate-700"
                      )}
                    />
                    <span>{item.name}</span>
                  </div>
                  {isActive && <ChevronRight className="h-3.5 w-3.5 text-teal-400" />}
                </Link>
              );
            })}
          </div>

          {/* System & Settings Section */}
          <div className="space-y-1 pt-2 border-t border-slate-100">
            <div className="px-2 mb-2 text-metadata text-[10px] text-slate-400">
              Administration
            </div>
            {systemNavigation.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2.5 rounded-md px-3 py-2 text-xs font-semibold transition-colors",
                    isActive
                      ? "bg-slate-900 text-white"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  )}
                >
                  <Icon
                    className={cn(
                      "h-4 w-4 shrink-0",
                      isActive ? "text-teal-400" : "text-slate-400"
                    )}
                  />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Operating Posture Status */}
        <div className="p-3 mx-3 mb-3 rounded-md bg-slate-50 border border-slate-200 text-slate-700 space-y-1">
          <div className="flex items-center justify-between text-[11px] font-semibold text-slate-800">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-teal-600" />
              ASSIST-ONLY Mode
            </span>
            <span className="font-mono text-[9px] text-slate-400">v1.0</span>
          </div>
          <p className="text-[10px] text-slate-500 leading-tight">
            Examiner sign-off required on all evaluated scripts.
          </p>
        </div>

        {/* Logout */}
        {onLogout && (
          <div className="border-t border-slate-200/80 p-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={onLogout}
              className="w-full justify-start text-xs text-slate-600 hover:bg-rose-50 hover:text-rose-700 rounded-md font-semibold"
            >
              <LogOut className="mr-2 h-4 w-4" /> Exit Session
            </Button>
          </div>
        )}
      </aside>
    </>
  );
};
Sidebar.displayName = "Sidebar";
