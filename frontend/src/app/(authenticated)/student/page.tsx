"use client";

import React, { useState, useEffect } from "react";
import { Users, Search, BookOpen, GraduationCap, ShieldCheck, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { SubmissionService } from "@/services/submission.service";

export default function StudentRosterPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [students, setStudents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadSubmissions() {
      try {
        const res = await SubmissionService.getSubmissions({ limit: 100 });
        if (res.success && res.data?.submissions) {
          const mapped = res.data.submissions.map((sub: any) => ({
            id: sub.id,
            roll: sub.student_roll_number,
            name: sub.student_name,
            exam: "Assessment", // Generic unless joined with exams
            score: sub.total_marks ? `${sub.obtained_marks || 0}/${sub.total_marks}` : "Pending",
            status: sub.status
          }));
          setStudents(mapped);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadSubmissions();
  }, []);

  const filtered = students.filter(
    (s) =>
      (s.name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.roll || "").toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <GraduationCap className="h-5 w-5 text-slate-800" />
            <h1 className="text-display text-xl">Student Examination Roster</h1>
          </div>
          <p className="text-caption text-xs">
            Student identities are anonymized during initial AI grading. Re-attached at result assembly.
          </p>
        </div>
        <Badge variant="academic" icon={<ShieldCheck className="h-3 w-3 text-teal-600" />}>
          DPDP Act 2023 Compliant Anonymization
        </Badge>
      </div>

      <div className="flex items-center justify-between gap-4">
        <Input
          placeholder="Search by student name, roll number, or assessment..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          leftIcon={<Search className="h-4 w-4" />}
          className="max-w-md"
        />
        <span className="text-metadata text-xs font-mono text-slate-500">
          Showing {filtered.length} Students
        </span>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Roll Number</TableHead>
            <TableHead>Student Name</TableHead>
            <TableHead>Assessment</TableHead>
            <TableHead className="text-right">Score</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            <TableRow>
              <TableCell colSpan={5} className="text-center py-8 text-slate-500">
                <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
                Loading roster...
              </TableCell>
            </TableRow>
          ) : filtered.length === 0 ? (
            <TableRow>
              <TableCell colSpan={5} className="text-center py-8 text-slate-500">
                No students found.
              </TableCell>
            </TableRow>
          ) : (
            filtered.map((s) => (
            <TableRow key={s.id}>
              <TableCell className="font-mono text-xs font-bold text-slate-900">{s.roll}</TableCell>
              <TableCell className="font-semibold text-slate-800">{s.name}</TableCell>
              <TableCell className="text-xs text-slate-600">{s.exam}</TableCell>
              <TableCell className="text-right font-mono font-bold text-slate-900">{s.score}</TableCell>
              <TableCell className="text-right">
                <Button size="xs" variant="outline">
                  View Student Report
                </Button>
              </TableCell>
            </TableRow>
          )))}
        </TableBody>
      </Table>
    </div>
  );
}
