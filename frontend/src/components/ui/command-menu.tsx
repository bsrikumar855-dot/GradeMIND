"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  LayoutDashboard,
  FileUp,
  BrainCircuit,
  FileText,
  BarChart3,
  MessageSquare,
  Sparkles,
  Command,
  X,
  ArrowRight,
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
        } else {
          // Open triggered from parent or global handler
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
      id: "dashboard",
      title: "Examination Workspace Overview",
      category: "Navigation",
      icon: LayoutDashboard,
      shortcut: "G D",
      url: "/dashboard",
    },
    {
      id: "upload",
      title: "Create Assessment / Upload Sheets",
      category: "Actions",
      icon: FileUp,
      shortcut: "N A",
      url: "/upload",
    },
    {
      id: "review",
      title: "Human Review Queue",
      category: "Audit",
      icon: Sparkles,
      shortcut: "G Q",
      url: "/review",
    },
    {
      id: "evaluation",
      title: "Live Pipeline Monitor",
      category: "Actions",
      icon: BrainCircuit,
      shortcut: "L P",
      url: "/evaluation",
    },
    {
      id: "results",
      title: "Evaluation Workspace & PDF View",
      category: "Navigation",
      icon: FileText,
      shortcut: "G R",
      url: "/results",
    },
    {
      id: "reports",
      title: "Academic Intelligence Reports",
      category: "Reports",
      icon: FileText,
      shortcut: "G I",
      url: "/reports",
    },
    {
      id: "analytics",
      title: "Cohort Performance Analytics",
      category: "Analytics",
      icon: BarChart3,
      shortcut: "G A",
      url: "/analytics",
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
      <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-slate-950/40 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: -10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: -10 }}
          transition={{ duration: 0.15, ease: "easeOut" }}
          className="w-full max-w-2xl bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden"
        >
          {/* Header Input */}
          <div className="relative flex items-center px-4 border-b border-slate-100">
            <Search className="w-5 h-5 text-slate-400 mr-3" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type a command or search assessments, reports, tools..."
              className="w-full py-4 text-sm bg-transparent border-none outline-none text-slate-900 placeholder:text-slate-400 font-medium"
              autoFocus
            />
            <button
              onClick={onClose}
              className="p-1 text-slate-400 hover:text-slate-600 rounded-md transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Results List */}
          <div className="max-h-96 overflow-y-auto p-2">
            {filtered.length === 0 ? (
              <div className="py-12 text-center text-sm text-slate-500">
                No commands or pages matching &quot;{query}&quot;
              </div>
            ) : (
              <div className="space-y-1">
                {filtered.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleSelect(item.url)}
                      className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 transition-colors group text-left"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-md bg-slate-100 group-hover:bg-indigo-50 text-slate-600 group-hover:text-indigo-600 transition-colors">
                          <Icon className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors">
                            {item.title}
                          </div>
                          <div className="text-xs text-slate-400">
                            {item.category}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
                          {item.shortcut}
                        </span>
                        <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-indigo-600 group-hover:translate-x-0.5 transition-all" />
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer Bar */}
          <div className="px-4 py-2.5 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px] font-mono shadow-2xl">
                  ↑↓
                </kbd>{" "}
                Navigate
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px] font-mono shadow-2xl">
                  ↵
                </kbd>{" "}
                Select
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px] font-mono shadow-2xl">
                  ESC
                </kbd>{" "}
                Dismiss
              </span>
            </div>
            <div className="flex items-center gap-1.5 font-medium text-slate-600">
              <Command className="w-3.5 h-3.5 text-indigo-600" />
              GradeMIND OS 2.0
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
