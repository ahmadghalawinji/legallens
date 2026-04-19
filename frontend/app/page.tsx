"use client";

import { UploadZone } from "@/components/upload/UploadZone";

export default function HomePage() {
  return (
    <div className="flex flex-col items-center gap-8 py-12">
      <div className="text-center max-w-2xl">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Understand Your Contract in Minutes
        </h1>
        <p className="text-lg text-gray-600">
          Upload a PDF or DOCX contract and our AI will extract risky clauses,
          explain them in plain English, and suggest fairer alternatives.
          <span className="block mt-2 text-sm text-gray-400">
            100% free — runs locally with Ollama or on Groq's free tier.
          </span>
        </p>
      </div>
      <UploadZone />
    </div>
  );
}
