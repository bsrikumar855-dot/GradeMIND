"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  UploadCloud,
  FileCheck2,
  ListTodo,
  MessageSquareReply,
  BarChart3,
  LogOut,
  Sparkles,
  Zap,
  X,
  ChevronRight
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

  const navigation = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard, badge: null },
    { name: "Upload Exam", href: "/upload", icon: UploadCloud, badge: "New" },
    { name: "AI Evaluation", href: "/evaluation", icon: FileCheck2, badge: "Live" },
    { name: "View Results", href: "/results", icon: ListTodo, badge: null },
    { name: "Teacher Feedback", href: "/feedback", icon: MessageSquareReply, badge: null },
    { name: "Analytical Reports", href: "/reports", icon: BarChart3, badge: null },
  ];

  return (
    <>
      {isOpen && (
        <div 
          className="fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm transition-opacity md:hidden" 
          onClick={onClose} 
        />
      )}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-slate-200/80 bg-white/90 backdrop-blur-xl shadow-xl transition-transform duration-300 md:translate-x-0",
        isOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        {/* Brand Header */}
        <div className="flex h-20 items-center justify-between px-6 border-b border-slate-100">
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-500 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-emerald-500/25 group-hover:scale-105 transition-transform">
              <Sparkles className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <span className="text-xl font-black tracking-tight text-slate-900 flex items-center gap-1">
                Grade<span className="text-emerald-600">MIND</span>
              </span>
              <span className="block text-[10px] font-bold text-slate-400 tracking-wider uppercase">
                Autonomous AI Grading
              </span>
            </div>
          </Link>
          {onClose && (
            <Button variant="ghost" size="sm" onClick={onClose} className="md:hidden h-8 w-8 p-0 text-slate-400 hover:text-slate-600">
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 space-y-1.5 px-4 py-6 overflow-y-auto">
          <div className="px-3 mb-2 text-[11px] font-bold text-slate-400 uppercase tracking-widest">
            Main Menu
          </div>
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
            return (
              <Link 
                key={item.name} 
                href={item.href} 
                className={cn(
                  "group relative flex items-center justify-between rounded-xl px-3.5 py-3 text-sm font-semibold transition-all duration-200",
                  isActive 
                    ? "bg-slate-900 text-white shadow-md shadow-slate-900/10" 
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                )}
              >
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "p-2 rounded-lg transition-colors",
                    isActive ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-100 text-slate-500 group-hover:bg-slate-200/60 group-hover:text-slate-900"
                  )}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className={cn(
                    "px-2 py-0.5 text-[10px] font-bold rounded-full uppercase tracking-wider",
                    item.badge === "Live" 
                      ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 animate-pulse" 
                      : "bg-blue-500/10 text-blue-600 border border-blue-500/20"
                  )}>
                    {item.badge}
                  </span>
                )}
                {isActive && (
                  <ChevronRight className="w-4 h-4 text-emerald-400 ml-auto" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* System Status Banner */}
        <div className="p-4 mx-4 mb-4 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 text-white border border-slate-700/50 shadow-xl">
          <div className="flex items-center gap-2 mb-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
              <Zap className="w-3.5 h-3.5 fill-emerald-400" /> Groq 120B AI Active
            </span>
          </div>
          <p className="text-[11px] text-slate-300 leading-snug">
            Engine running at <span className="font-bold text-white">~1.2s per script</span> evaluation with 99.4% precision.
          </p>
        </div>

        {/* Logout */}
        {onLogout && (
          <div className="border-t border-slate-100 p-4">
            <Button 
              variant="ghost" 
              onClick={onLogout} 
              className="w-full justify-start text-slate-500 hover:bg-rose-50 hover:text-rose-600 rounded-xl font-semibold transition-colors"
            >
              <LogOut className="mr-3 h-4 w-4" /> Logout Session
            </Button>
          </div>
        )}
      </aside>
    </>
  );
};
Sidebar.displayName = "Sidebar";
