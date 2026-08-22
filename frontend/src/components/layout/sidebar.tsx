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
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Upload", href: "/upload", icon: UploadCloud },
    { name: "Evaluation", href: "/evaluation", icon: FileCheck2 },
    { name: "Review", href: "/review", icon: ListTodo },
    { name: "Results", href: "/results", icon: MessageSquareReply },
    { name: "Analytics", href: "/analytics", icon: BarChart3 },
    { name: "Reports", href: "/reports", icon: BarChart3 },
  ];

  return (
    <>
      {isOpen && (
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs transition-opacity md:hidden" 
          onClick={onClose} 
        />
      )}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r border-emerald-800/30 bg-[#F4F8F3] transition-transform duration-300 md:translate-x-0",
        isOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        {/* Brand Header with Double-Color Logo Text */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-emerald-800/20 bg-white">
          <Link href="/dashboard" className="flex items-center gap-2.5 group">
            <div className="relative w-9 h-9 rounded-xl overflow-hidden shadow-xs border-2 border-[#183B25] bg-[#183B25] flex items-center justify-center shrink-0">
              <img 
                src="/images/logo.png" 
                alt="GradeMIND Logo" 
                className="w-full h-full object-cover group-hover:scale-110 group-hover:rotate-3 transition-transform duration-300"
              />
            </div>
            <div>
              <span className="text-lg font-black tracking-tight font-serif flex items-center gap-0">
                <span className="text-[#183B25]">Grade</span>
                <span className="text-[#4A8B40]">MIND</span>
              </span>
              <span className="block text-[8.5px] font-bold text-black tracking-wider uppercase">
                Examination Workspace
              </span>
            </div>
          </Link>
          {onClose && (
            <Button variant="ghost" size="sm" onClick={onClose} className="md:hidden h-8 w-8 p-0 text-black hover:text-emerald-900">
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 space-y-1.5 px-3 py-4 overflow-y-auto">
          <div className="px-3 mb-2 text-[9.5px] font-extrabold text-black uppercase tracking-widest">
            Workspace Navigation
          </div>
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
            return (
              <Link 
                key={item.name} 
                href={item.href} 
                className={cn(
                  "group relative flex items-center justify-between rounded-xl px-3 py-2.5 text-xs font-bold transition-all duration-200",
                  isActive 
                    ? "bg-[#183B25] text-white shadow-sm" 
                    : "text-black hover:bg-emerald-100/90 hover:text-black"
                )}
              >
                <div className="flex items-center gap-2.5">
                  <div className={cn(
                    "p-1.5 rounded-lg transition-all duration-300 group-hover:scale-110 group-hover:rotate-3",
                    isActive ? "bg-emerald-700/60 text-emerald-300" : "bg-emerald-100 text-[#183B25] group-hover:bg-white group-hover:text-black"
                  )}>
                    <Icon className="h-4 w-4 transition-transform duration-300 group-hover:scale-110" />
                  </div>
                  <span className={isActive ? "text-white font-black" : "text-black font-extrabold"}>{item.name}</span>
                </div>
                {isActive && (
                  <ChevronRight className="w-3.5 h-3.5 text-emerald-400 ml-auto animate-pulse" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* System Status Banner */}
        <div className="p-3.5 mx-3 mb-3 rounded-xl bg-[#183B25] text-white border-2 border-emerald-700/60 shadow-xs relative overflow-hidden group">
          <div className="flex items-center gap-2 mb-1">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
            </span>
            <span className="text-[10px] font-bold text-emerald-300 uppercase tracking-wider">
              Grading Engine Active
            </span>
          </div>
          <p className="text-[11px] text-white leading-snug font-medium">
            Autonomous evaluation & OCR ready for processing.
          </p>
        </div>

        {/* Logout */}
        {onLogout && (
          <div className="border-t border-emerald-800/20 p-3 bg-white">
            <Button 
              variant="ghost" 
              onClick={onLogout} 
              className="w-full justify-start text-xs text-black hover:bg-rose-50 hover:text-rose-700 rounded-xl font-bold transition-colors group"
            >
              <LogOut className="mr-2.5 h-4 w-4 text-rose-600 group-hover:rotate-12 transition-transform duration-300" /> Logout Session
            </Button>
          </div>
        )}
      </aside>
    </>
  );
};
Sidebar.displayName = "Sidebar";
