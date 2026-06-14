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
  X
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
    { name: "Upload Exam", href: "/upload", icon: UploadCloud },
    { name: "AI Evaluation", href: "/evaluation", icon: FileCheck2 },
    { name: "View Results", href: "/results", icon: ListTodo },
    { name: "Teacher Feedback", href: "/feedback", icon: MessageSquareReply },
    { name: "Analytical Reports", href: "/reports", icon: BarChart3 },
  ];

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm transition-opacity md:hidden" onClick={onClose} />
      )}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-gray-100 bg-white transition-transform md:translate-x-0",
        isOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="flex h-16 items-center justify-between px-6 border-b border-gray-50">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-primary flex items-center justify-center shadow-sm">
              <span className="text-white font-bold text-xl leading-none">G</span>
            </div>
            <span className="text-xl font-bold text-brand-dark tracking-tight">GradeMIND</span>
          </div>
          {onClose && (
            <Button variant="ghost" size="sm" onClick={onClose} className="md:hidden h-8 w-8 p-0 text-gray-500">
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
        <nav className="flex-1 space-y-2 px-4 py-6 overflow-y-auto">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link key={item.name} href={item.href} className={cn(
                "group flex items-center rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200",
                isActive ? "bg-brand-secondary text-brand-dark" : "text-gray-500 hover:bg-gray-50 hover:text-brand-dark"
              )}>
                <Icon className={cn("mr-3 h-5 w-5 flex-shrink-0 transition-colors", isActive ? "text-brand-primary" : "text-gray-400 group-hover:text-brand-primary")} />
                {item.name}
              </Link>
            );
          })}
        </nav>
        {onLogout && (
          <div className="border-t border-gray-50 p-4">
            <Button variant="ghost" onClick={onLogout} className="w-full justify-start text-gray-500 hover:bg-red-50 hover:text-red-600 rounded-xl">
              <LogOut className="mr-3 h-5 w-5" /> Logout
            </Button>
          </div>
        )}
      </aside>
    </>
  );
};
Sidebar.displayName = "Sidebar";
