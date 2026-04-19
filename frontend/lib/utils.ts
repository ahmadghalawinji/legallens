import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { RiskLevel } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function riskColor(level: RiskLevel): string {
  return { high: "text-red-600", medium: "text-amber-600", low: "text-green-600" }[level];
}

export function riskBg(level: RiskLevel): string {
  return {
    high: "bg-red-50 border-red-200",
    medium: "bg-amber-50 border-amber-200",
    low: "bg-green-50 border-green-200",
  }[level];
}

export function riskBadge(level: RiskLevel): string {
  return {
    high: "bg-red-100 text-red-700",
    medium: "bg-amber-100 text-amber-700",
    low: "bg-green-100 text-green-700",
  }[level];
}

export function formatClauseType(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}
