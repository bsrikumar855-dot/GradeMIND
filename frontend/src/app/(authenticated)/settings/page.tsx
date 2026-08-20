"use client";

import React from "react";
import { Settings, ShieldCheck, Cpu, Database } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-display text-xl flex items-center gap-2">
            <Settings className="h-5 w-5 text-slate-800" /> Platform Settings
          </h1>
          <p className="text-caption text-xs">
            Configure system verification thresholds, evaluation modes, and security controls.
          </p>
        </div>
        <Badge variant="academic">GradeMIND OS 2.0</Badge>
      </div>

      <div className="space-y-4">
        <div className="calm-card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-teal-600" />
            <h3 className="text-heading text-sm font-bold">Operating Posture & Lane Routing</h3>
          </div>
          <div className="p-3 bg-slate-50 border border-slate-200 rounded text-xs space-y-1">
            <span className="font-bold text-slate-900 block">ASSIST-ONLY Execution Mode Active</span>
            <p className="text-slate-600 leading-relaxed">
              Every question is routed to REVIEW or MANDATORY_HUMAN lane. Autonomous single-authority scoring is disabled per system compliance configuration.
            </p>
          </div>
        </div>

        <div className="calm-card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-slate-800" />
            <h3 className="text-heading text-sm font-bold">Verification Engine Thresholds</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input label="Score Disagreement Threshold (Marks)" defaultValue="2.0" readOnly />
            <Input label="Confidence Gap Threshold (%)" defaultValue="30%" readOnly />
          </div>
        </div>

        <div className="calm-card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-slate-800" />
            <h3 className="text-heading text-sm font-bold">Compliance & Audit Trail</h3>
          </div>
          <p className="text-xs text-slate-600">
            Immutable append-only audit logs track all mark modifications and examiner sign-offs in accordance with DPDP Act 2023.
          </p>
        </div>
      </div>
    </div>
  );
}
