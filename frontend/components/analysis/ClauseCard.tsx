import type { ClassifiedClause } from "@/lib/types";
import { cn, riskBadge, riskBg, formatClauseType, formatScore } from "@/lib/utils";
import { ChevronRight } from "lucide-react";

interface ClauseCardProps {
  clause: ClassifiedClause;
  onClick: () => void;
}

export function ClauseCard({ clause, onClick }: ClauseCardProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left border rounded-xl p-4 flex items-start gap-4 hover:shadow-md transition-shadow",
        riskBg(clause.risk_level)
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span
            className={cn(
              "text-xs font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide",
              riskBadge(clause.risk_level)
            )}
          >
            {clause.risk_level}
          </span>
          <span className="text-xs text-gray-500">
            {formatClauseType(clause.clause_type)}
          </span>
          <span className="text-xs text-gray-400 ml-auto">
            Risk: {formatScore(clause.risk_score)}
          </span>
        </div>
        <p className="text-sm text-gray-800 line-clamp-2">{clause.text}</p>
        <p className="text-xs text-gray-500 mt-1 line-clamp-1">{clause.risk_explanation}</p>
      </div>
      <ChevronRight className="w-4 h-4 text-gray-400 shrink-0 mt-1" />
    </button>
  );
}
