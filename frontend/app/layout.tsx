import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LegalLens — AI Contract Risk Analyzer",
  description:
    "Upload a contract and get an instant AI-powered risk analysis with plain-language explanations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <nav className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="max-w-6xl mx-auto flex items-center gap-2">
            <span className="text-xl font-bold text-gray-900">⚖️ LegalLens</span>
            <span className="text-sm text-gray-500 ml-2">AI Contract Risk Analyzer</span>
          </div>
        </nav>
        <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
        <footer className="mt-16 border-t border-gray-200 px-6 py-4 text-center text-xs text-gray-400">
          LegalLens is not legal advice. Always consult a qualified attorney before signing contracts.
        </footer>
      </body>
    </html>
  );
}
