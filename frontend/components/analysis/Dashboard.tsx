"use client";

import { useState } from "react";
import type { AnalysisResult, ClassifiedClause } from "@/lib/types";
import { SummaryCard } from "./SummaryCard";
import { ClauseCard } from "./ClauseCard";
import { ClauseDialog } from "./ClauseDialog";

interface DashboardProps {
  result: AnalysisResult;
}

export function Dashboard({ result }: DashboardProps) {
  const [selected, setSelected] = useState<ClassifiedClause | null>(null);
  const [filter, setFilter] = useState<"all" | "high" | "medium" | "low">("all");

  const filtered =
    filter === "all" ? result.clauses : result.clauses.filter((c) => c.risk_level === filter);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analysis Results</h1>
          <p className="text-sm text-gray-500 mt-1">{result.filename}</p>
        </div>
        <a href="/" className="text-sm text-blue-600 hover:underline">
          ← New analysis
        </a>
      </div>

      <SummaryCard result={result} />

      {/* Filter bar */}
      <div className="flex gap-2 flex-wrap">
        {(["all", "high", "medium", "low"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-full text-sm font-medium border transition-colors ${
              filter === f
                ? "bg-gray-900 text-white border-gray-900"
                : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
            }`}
          >
            {f === "all" ? `All (${result.clauses.length})` : `${f.charAt(0).toUpperCase() + f.slice(1)} (${result.clauses.filter((c) => c.risk_level === f).length})`}
          </button>
        ))}
      </div>

      {/* Clause list */}
      {filtered.length === 0 ? (
        <p className="text-gray-400 text-sm py-8 text-center">No clauses match this filter.</p>
      ) : (
        <div className="grid gap-3">
          {filtered.map((clause) => (
            <ClauseCard
              key={clause.id}
              clause={clause}
              onClick={() => setSelected(clause)}
            />
          ))}
        </div>
      )}

      {selected && (
        <ClauseDialog clause={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
