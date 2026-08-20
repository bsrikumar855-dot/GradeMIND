"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  LayoutDashboard,
  FileUp,
  ListTodo,
  FileText,
  BarChart3,
  Users,
  Settings,
  HelpCircle,
  X,
  ArrowRight,
  Command as CommandIcon,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface CommandMenuProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandMenu({ isOpen, onClose }: CommandMenuProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (isOpen) {
          onClose();
        }
      }
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const actions = [
    {
      id: "create-assessment",
      title: "Create Assessment",
      category: "Assessments",
      icon: FileUp,
      shortcut: "N A",
      url: "/upload",
    },
    {
      id: "upload-sheets",
      title: "Upload Answer Sheets",
      category: "Assessments",
      icon: FileUp,
      shortcut: "U S",
      url: "/upload",
    },
    {
      id: "search-assessment",
      title: "Search Assessment Workspace",
      category: "Search",
      icon: LayoutDashboard,
      shortcut: "G D",
      url: "/dashboard",
    },
    {
      id: "search-student",
      title: "Search Student Roster",
      category: "Students",
      icon: Users,
      shortcut: "G S",
      url: "/student",
    },
    {
      id: "open-review-queue",
      title: "Open Review Queue",
      category: "Audit",
      icon: ListTodo,
      shortcut: "G Q",
      url: "/review",
    },
    {
      id: "view-reports",
      title: "View Examination Reports",
      category: "Reports",
      icon: FileText,
      shortcut: "G R",
      url: "/reports",
    },
    {
      id: "open-analytics",
      title: "Open Performance Analytics",
      category: "Analytics",
      icon: BarChart3,
      shortcut: "G A",
      url: "/analytics",
    },
    {
      id: "settings",
      title: "Platform Settings",
      category: "System",
      icon: Settings,
      shortcut: "G S",
      url: "/settings",
    },
  ];

  const filtered = actions.filter(
    (item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      item.category.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (url: string) => {
    router.push(url);
    onClose();
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-slate-950/40 backdrop-blur-xs">
        <motion.div
          initial={{ opacity: 0, scale: 0.98, y: -8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.98, y: -8 }}
          transition={{ duration: 0.12, ease: "easeOut" }}
          className="w-full max-w-xl bg-white rounded-lg shadow-xl border border-slate-200 overflow-hidden"
        >
          {/* Header Input */}
          <div className="relative flex items-center px-4 border-b border-slate-200">
            <Search className="w-4 h-4 text-slate-400 mr-3 shrink-0" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type a command or search assessments, students, reports..."
              className="w-full py-3.5 text-sm bg-transparent border-none outline-none text-slate-900 placeholder:text-slate-400 font-medium"
              autoFocus
            />
            <button
              onClick={onClose}
              className="p-1 text-slate-400 hover:text-slate-600 rounded-md transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Command List */}
          <div className="max-h-80 overflow-y-auto p-2">
            {filtered.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500">
                No commands matching &quot;{query}&quot;
              </div>
            ) : (
              <div className="space-y-1">
                {filtered.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleSelect(item.url)}
                      className="w-full flex items-center justify-between p-2.5 rounded-md hover:bg-slate-100 transition-colors group text-left cursor-pointer"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-1.5 rounded bg-slate-100 text-slate-600 group-hover:bg-slate-200 group-hover:text-slate-900 transition-colors">
                          <Icon className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="text-xs font-bold text-slate-900">
                            {item.title}
                          </div>
                          <div className="text-[10px] text-slate-400 font-medium">
                            {item.category}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
                          {item.shortcut}
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-700 transition-colors" />
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer Bar */}
          <div className="px-4 py-2 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500 font-medium">
            <div className="flex items-center gap-3">
              <span><kbd className="px-1 py-0.5 bg-white border border-slate-200 rounded text-[10px] font-mono">↑↓</kbd> Navigate</span>
              <span><kbd className="px-1 py-0.5 bg-white border border-slate-200 rounded text-[10px] font-mono">↵</kbd> Select</span>
              <span><kbd className="px-1 py-0.5 bg-white border border-slate-200 rounded text-[10px] font-mono">ESC</kbd> Close</span>
            </div>
            <div className="flex items-center gap-1 text-slate-600 font-mono">
              <CommandIcon className="w-3 h-3 text-teal-600" /> GradeMIND OS
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
