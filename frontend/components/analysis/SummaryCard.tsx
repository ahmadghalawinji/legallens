import type { AnalysisResult } from "@/lib/types";
import { formatScore } from "@/lib/utils";

interface SummaryCardProps {
  result: AnalysisResult;
}

export function SummaryCard({ result }: SummaryCardProps) {
  const score = result.overall_risk_score;
  const scoreColor =
    score >= 0.6 ? "text-red-600" : score >= 0.35 ? "text-amber-600" : "text-green-600";

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
        <div>
          <p className="text-sm text-gray-500 uppercase tracking-wide font-medium">
            Overall Risk Score
          </p>
          <p className={`text-5xl font-bold mt-1 ${scoreColor}`}>
            {formatScore(score)}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Analyzed in {result.processing_time_seconds}s
          </p>
        </div>

        <div className="flex gap-6">
          <Stat label="High Risk" value={result.high_risk_count} color="text-red-600" />
          <Stat label="Medium Risk" value={result.medium_risk_count} color="text-amber-600" />
          <Stat label="Low Risk" value={result.low_risk_count} color="text-green-600" />
        </div>
      </div>

      <p className="text-xs text-gray-400 mt-4 italic">
        This is not legal advice. Consult a qualified attorney before signing.
      </p>
    </div>
  );
}

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="text-center">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}
