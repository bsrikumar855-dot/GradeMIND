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
    { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
    { name: "Assessments", href: "/upload", icon: UploadCloud },
    { name: "Evaluation", href: "/evaluation", icon: FileCheck2 },
    { name: "Review Queue", href: "/review", icon: ListTodo },
    { name: "Results Workspace", href: "/results", icon: MessageSquareReply },
    { name: "Analytics", href: "/analytics", icon: BarChart3 },
    { name: "Reports", href: "/reports", icon: BarChart3 },
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
        "fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-slate-200/80 bg-white/95 backdrop-blur-xl shadow-xl transition-transform duration-300 md:translate-x-0",
        isOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between px-6 border-b border-slate-100">
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-slate-900 flex items-center justify-center text-emerald-400 font-black text-sm shadow-md">
              GM
            </div>
            <div>
              <span className="text-lg font-black tracking-tight text-slate-900 flex items-center gap-1">
                Grade<span className="text-emerald-600">MIND</span>
              </span>
              <span className="block text-[10px] font-bold text-slate-400 tracking-wider uppercase">
                Examination Workspace
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
        <nav className="flex-1 space-y-1 px-4 py-4 overflow-y-auto">
          <div className="px-3 mb-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Workspace
          </div>
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
            return (
              <Link 
                key={item.name} 
                href={item.href} 
                className={cn(
                  "group relative flex items-center justify-between rounded-xl px-3 py-2.5 text-xs font-bold transition-all duration-150",
                  isActive 
                    ? "bg-slate-900 text-white shadow-sm" 
                    : "text-slate-600 hover:bg-slate-100/80 hover:text-slate-900"
                )}
              >
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "p-1.5 rounded-lg transition-colors",
                    isActive ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-100 text-slate-500 group-hover:bg-slate-200/60 group-hover:text-slate-900"
                  )}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <span>{item.name}</span>
                </div>
                {isActive && (
                  <ChevronRight className="w-3.5 h-3.5 text-emerald-400 ml-auto" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* System Status Banner */}
        <div className="p-4 mx-4 mb-4 rounded-xl bg-slate-900 text-white border border-slate-800 shadow-sm">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider">
              Grading Engine Active
            </span>
          </div>
          <p className="text-[11px] text-slate-400 leading-snug">
            Autonomous evaluation & OCR ready for submission processing.
          </p>
        </div>

        {/* Logout */}
        {onLogout && (
          <div className="border-t border-slate-100 p-3">
            <Button 
              variant="ghost" 
              onClick={onLogout} 
              className="w-full justify-start text-xs text-slate-500 hover:bg-rose-50 hover:text-rose-600 rounded-xl font-bold transition-colors"
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
