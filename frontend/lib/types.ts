export type ClauseType =
  | "liability"
  | "indemnification"
  | "ip_assignment"
  | "confidentiality"
  | "termination"
  | "payment_terms"
  | "non_compete"
  | "governing_law"
  | "dispute_resolution"
  | "auto_renewal"
  | "data_protection"
  | "force_majeure"
  | "other";

export type RiskLevel = "low" | "medium" | "high";
export type TaskStatus = "pending" | "processing" | "completed" | "failed";

export interface ClassifiedClause {
  id: string;
  clause_type: ClauseType;
  text: string;
  confidence: number;
  page_number: number | null;
  risk_level: RiskLevel;
  risk_score: number;
  risk_explanation: string;
  reasoning: string;
}

export interface AnalysisResult {
  filename: string;
  clauses: ClassifiedClause[];
  overall_risk_score: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  processing_time_seconds: number;
}

export interface TaskResponse {
  task_id: string;
  status: TaskStatus;
  progress: number;
  result: AnalysisResult | null;
  error: string | null;
}

export interface ApiEnvelope<T> {
  status: string;
  data: T | null;
  errors: string[] | null;
  metadata: Record<string, unknown> | null;
}
