"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileText, AlertCircle } from "lucide-react";
import { uploadContract, pollUntilComplete } from "@/lib/api";
import { cn } from "@/lib/utils";

const ACCEPTED = [".pdf", ".docx"];
const MAX_MB = 20;

export function UploadZone() {
  const router = useRouter();
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const validate = (f: File): string | null => {
    const ext = "." + f.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED.includes(ext)) return `Unsupported type. Upload a PDF or DOCX file.`;
    if (f.size > MAX_MB * 1024 * 1024) return `File too large. Maximum size is ${MAX_MB}MB.`;
    return null;
  };

  const handleFile = useCallback(
    async (f: File) => {
      const err = validate(f);
      if (err) { setError(err); return; }
      setFile(f);
      setError(null);
      setLoading(true);
      setStatus("Uploading…");
      setProgress(5);

      try {
        const { task_id } = await uploadContract(f);
        setStatus("Analysis started…");

        await pollUntilComplete(
          task_id,
          (pct, st) => {
            setProgress(pct);
            setStatus(
              st === "processing"
                ? pct < 40 ? "Parsing document…" : pct < 70 ? "Extracting clauses…" : "Classifying risks…"
                : st
            );
          }
        );

        router.push(`/analysis/${task_id}`);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Something went wrong.");
        setLoading(false);
        setStatus("");
        setProgress(0);
      }
    },
    [router]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  };

  return (
    <div className="w-full max-w-xl">
      <label
        className={cn(
          "flex flex-col items-center justify-center w-full h-56 border-2 border-dashed rounded-xl cursor-pointer transition-colors",
          dragging ? "border-blue-400 bg-blue-50" : "border-gray-300 bg-white hover:border-blue-300 hover:bg-blue-50",
          loading && "pointer-events-none opacity-60"
        )}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          type="file"
          className="sr-only"
          accept=".pdf,.docx"
          onChange={onInputChange}
          disabled={loading}
        />
        {loading ? (
          <div className="flex flex-col items-center gap-3 px-6 w-full">
            <FileText className="w-10 h-10 text-blue-500" />
            <p className="text-sm font-medium text-gray-700">{file?.name}</p>
            <p className="text-xs text-gray-500">{status}</p>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-gray-400">{progress}%</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 text-center px-6">
            <Upload className="w-10 h-10 text-gray-400" />
            <div>
              <p className="text-sm font-medium text-gray-700">
                Drag & drop or <span className="text-blue-600 underline">browse</span>
              </p>
              <p className="text-xs text-gray-400 mt-1">PDF or DOCX up to 20MB</p>
            </div>
          </div>
        )}
      </label>

      {error && (
        <div className="mt-3 flex items-start gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          {error}
        </div>
      )}
    </div>
  );
}
