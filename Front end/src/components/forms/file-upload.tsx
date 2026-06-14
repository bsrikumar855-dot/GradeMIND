"use client";

import * as React from "react";
import { Upload, File, X, CheckCircle2, AlertCircle } from "lucide-react";
import { cn } from "@/utils/cn";
import { Button } from "@/components/ui/button";

export interface FileUploadProps {
  onFilesSelected?: (files: File[]) => void;
  maxSizeMB?: number;
  acceptedTypes?: string[];
  multiple?: boolean;
}

interface UploadQueueItem {
  id: string;
  file: File;
  progress: number;
  status: "pending" | "uploading" | "completed" | "failed";
  error?: string;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onFilesSelected,
  maxSizeMB = 10,
  acceptedTypes = [".pdf", ".png", ".jpg", ".jpeg"],
  multiple = true,
}) => {
  const [isDragActive, setIsDragActive] = React.useState(false);
  const [queue, setQueue] = React.useState<UploadQueueItem[]>([]);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  };

  const processFiles = (filesList: FileList | null) => {
    if (!filesList) return;
    const acceptedFiles: File[] = [];

    const newItems: UploadQueueItem[] = Array.from(filesList).map((file) => {
      const sizeMB = file.size / (1024 * 1024);
      const fileExtension = "." + file.name.split(".").pop()?.toLowerCase();
      const isTypeAccepted =
        acceptedTypes.length === 0 || acceptedTypes.includes(fileExtension);
      const isSizeOk = sizeMB <= maxSizeMB;

      let status: UploadQueueItem["status"] = "pending";
      let error: string | undefined = undefined;

      if (!isTypeAccepted) {
        status = "failed";
        error = `Invalid file type. Supported types: ${acceptedTypes.join(", ")}`;
      } else if (!isSizeOk) {
        status = "failed";
        error = `File exceeds max size limit of ${maxSizeMB}MB`;
      } else {
        acceptedFiles.push(file);
      }

      return {
        id: Math.random().toString(36).substring(7),
        file,
        progress: status === "failed" ? 0 : 100, // mock upload completion directly or upload state
        status,
        error,
      };
    });

    setQueue((prev) => (multiple ? [...prev, ...newItems] : newItems));
    if (onFilesSelected && acceptedFiles.length > 0) {
      onFilesSelected(acceptedFiles);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(e.dataTransfer.files);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFiles(e.target.files);
    }
  };

  const removeQueueItem = (id: string) => {
    setQueue((prev) => prev.filter((item) => item.id !== id));
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="w-full space-y-4">
      {/* Drag & Drop Zone */}
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-white p-8 text-center cursor-pointer transition-all duration-200 select-none hover:border-blue-500 hover:bg-blue-50/10 dark:border-gray-800 dark:bg-gray-950 dark:hover:border-blue-500/50",
          isDragActive && "border-blue-600 bg-blue-50/20 dark:border-blue-500 dark:bg-blue-950/10 scale-[1.01]"
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          multiple={multiple}
          onChange={handleInputChange}
          accept={acceptedTypes.join(",")}
        />

        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
          <Upload className="h-6 w-6 animate-pulse" />
        </div>

        <h3 className="mt-4 text-sm font-semibold text-gray-950 dark:text-gray-50">
          Drag and drop exam files
        </h3>
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          or <span className="font-bold text-blue-600 hover:underline">browse files</span> on your computer
        </p>
        <p className="mt-1.5 text-[10px] text-gray-400 dark:text-gray-550">
          Supports: {acceptedTypes.join(", ")} up to {maxSizeMB}MB
        </p>
      </div>

      {/* Upload Queue list */}
      {queue.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-950 space-y-3">
          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
            Selected Files ({queue.length})
          </h4>
          <div className="divide-y divide-gray-100 dark:divide-gray-900 max-h-60 overflow-y-auto pr-1">
            {queue.map((item) => (
              <div key={item.id} className="flex items-center justify-between py-2.5 gap-4 first:pt-0 last:pb-0">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-50 text-gray-500 dark:bg-gray-900 dark:text-gray-400">
                    <File className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 space-y-0.5">
                    <p className="text-sm font-semibold text-gray-950 dark:text-gray-50 truncate">
                      {item.file.name}
                    </p>
                    <p className="text-xs text-gray-400 font-medium">
                      {formatFileSize(item.file.size)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4 shrink-0">
                  {item.status === "completed" && (
                    <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 className="h-4 w-4" /> Ready
                    </span>
                  )}
                  {item.status === "failed" && (
                    <span
                      className="flex items-center gap-1.5 text-xs font-bold text-red-600 dark:text-red-400"
                      title={item.error}
                    >
                      <AlertCircle className="h-4 w-4" /> Error
                    </span>
                  )}

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeQueueItem(item.id)}
                    className="h-8 w-8 p-0 text-gray-400 hover:text-red-500"
                  >
                    <X className="h-4 w-4" />
                    <span className="sr-only">Remove</span>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

FileUpload.displayName = "FileUpload";
