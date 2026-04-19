"use client";

import { use, useEffect, useState } from "react";
import { getTaskStatus } from "@/lib/api";
import type { AnalysisResult } from "@/lib/types";
import { Dashboard } from "@/components/analysis/Dashboard";

export default function AnalysisPage({
  params,
}: {
  params: Promise<{ taskId: string }>;
}) {
  const { taskId } = use(params);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTaskStatus(taskId)
      .then((task) => {
        if (task.result) setResult(task.result);
        else if (task.status === "failed") setError(task.error ?? "Analysis failed");
        else setError("Result not yet available. Refresh in a moment.");
      })
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load results")
      );
  }, [taskId]);

  if (error)
    return (
      <div className="text-center py-20 text-red-600">
        <p className="text-lg font-medium">{error}</p>
        <a href="/" className="mt-4 inline-block text-blue-600 underline text-sm">
          ← Analyze another contract
        </a>
      </div>
    );

  if (!result)
    return (
      <div className="flex flex-col items-center py-20 gap-4 text-gray-500">
        <div className="w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin" />
        <p>Loading results…</p>
      </div>
    );

  return <Dashboard result={result} />;
}
