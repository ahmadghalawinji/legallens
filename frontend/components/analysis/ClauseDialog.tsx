"use client";

import { X } from "lucide-react";
import type { ClassifiedClause } from "@/lib/types";
import { cn, riskBadge, riskColor, formatClauseType, formatScore } from "@/lib/utils";

interface ClauseDialogProps {
  clause: ClassifiedClause;
  onClose: () => void;
}

export function ClauseDialog({ clause, onClose }: ClauseDialogProps) {
  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-gray-100">
          <div>
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "text-xs font-semibold px-2 py-0.5 rounded-full uppercase",
                  riskBadge(clause.risk_level)
                )}
              >
                {clause.risk_level} risk
              </span>
              <span className="text-sm text-gray-500">
                {formatClauseType(clause.clause_type)}
              </span>
            </div>
            <p className={cn("text-lg font-semibold mt-1", riskColor(clause.risk_level))}>
              Risk Score: {formatScore(clause.risk_score)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Original clause */}
          <Section title="Original Clause">
            <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3 font-mono leading-relaxed">
              {clause.text}
            </p>
          </Section>

          {/* Risk explanation */}
          <Section title="Risk Explanation">
            <p className="text-sm text-gray-700">{clause.risk_explanation}</p>
          </Section>

          {/* Reasoning */}
          <Section title="Analysis Reasoning">
            <p className="text-sm text-gray-600 whitespace-pre-line leading-relaxed">
              {clause.reasoning}
            </p>
          </Section>

          <p className="text-xs text-gray-400 italic pt-2 border-t border-gray-100">
            This is not legal advice. Consult a qualified attorney before signing.
          </p>
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
        {title}
      </h3>
      {children}
    </div>
  );
}
