"use client";

import { use, useEffect, useState } from "react";
import { publicApi, type Idea, type Report } from "@/lib/api";
import { FinancialDashboard } from "@/components/FinancialDashboard";

export default function PublicIdeaPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const [idea, setIdea] = useState<Idea | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchPublicIdea() {
      try {
        const res = await publicApi.getIdea(slug);
        setIdea(res.idea);
        setReports(res.reports);
      } catch (e: any) {
        setError(e.message || "Failed to load public idea");
      } finally {
        setLoading(false);
      }
    }
    fetchPublicIdea();
  }, [slug]);

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white p-8 md:p-16 flex justify-center items-center">
        <div className="animate-spin text-4xl">🚀</div>
      </div>
    );
  }

  if (error || !idea) {
    return (
      <div className="min-h-screen bg-black text-white p-8 md:p-16 flex flex-col justify-center items-center">
        <h1 className="text-3xl font-bold text-red-500 mb-4">Oops!</h1>
        <p className="text-zinc-400">{error || "Idea not found"}</p>
      </div>
    );
  }

  // Get Market Analyst and Tech Architect reports to showcase
  const marketReport = reports.find(r => r.report_type === "market_research");
  const techReport = reports.find(r => r.report_type === "tech_architecture");
  const financialReport = reports.find(r => r.report_type === "financial_projection");

  return (
    <div className="min-h-screen bg-black text-white selection:bg-indigo-500/30">
      {/* Hero Section */}
      <div className="relative overflow-hidden border-b border-zinc-800">
        <div className="absolute inset-0 bg-gradient-to-b from-indigo-500/10 to-black/0 pointer-events-none" />
        <div className="max-w-5xl mx-auto px-6 py-24 md:py-32 relative z-10">
          <div className="inline-flex items-center space-x-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-3 py-1 mb-8">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
            <span className="text-sm font-medium text-indigo-300">Incubated by AI Start-up Simulator</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-r from-white to-zinc-500">
            {idea.title}
          </h1>
          <p className="text-xl md:text-2xl text-zinc-400 max-w-3xl leading-relaxed">
            {idea.description}
          </p>
          
          <div className="mt-12 flex flex-wrap gap-4">
            {idea.industry && (
              <div className="px-4 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-300">
                <span className="text-zinc-500 mr-2">Industry</span> {idea.industry}
              </div>
            )}
            {idea.target_market && (
              <div className="px-4 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-300">
                <span className="text-zinc-500 mr-2">Market</span> {idea.target_market}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-16 space-y-24">
        
        {/* Problem / Solution */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
          {idea.problem_statement && (
            <div>
              <h2 className="text-2xl font-semibold mb-4 flex items-center">
                <span className="bg-red-500/10 text-red-400 p-2 rounded-lg mr-3">❌</span>
                The Problem
              </h2>
              <p className="text-zinc-400 leading-relaxed text-lg">{idea.problem_statement}</p>
            </div>
          )}
          {idea.proposed_solution && (
            <div>
              <h2 className="text-2xl font-semibold mb-4 flex items-center">
                <span className="bg-emerald-500/10 text-emerald-400 p-2 rounded-lg mr-3">💡</span>
                The Solution
              </h2>
              <p className="text-zinc-400 leading-relaxed text-lg">{idea.proposed_solution}</p>
            </div>
          )}
        </div>

        {/* Financial Dashboard */}
        {financialReport && typeof financialReport.content === 'string' && (
          <div>
            <h2 className="text-3xl font-bold mb-8">Financial Projections</h2>
            <FinancialDashboard content={financialReport.content} />
          </div>
        )}

        {/* Market Research */}
        {marketReport && (
          <div>
            <h2 className="text-3xl font-bold mb-8">Market Analysis</h2>
            <div className="prose prose-invert prose-lg max-w-none bg-zinc-900 border border-zinc-800 p-8 rounded-2xl">
              <div dangerouslySetInnerHTML={{ __html: marketReport.content as unknown as string }} />
            </div>
          </div>
        )}

        {/* Tech Architecture */}
        {techReport && (
          <div>
            <h2 className="text-3xl font-bold mb-8">Technical Architecture</h2>
            <div className="prose prose-invert prose-lg max-w-none bg-zinc-900 border border-zinc-800 p-8 rounded-2xl">
              <div dangerouslySetInnerHTML={{ __html: techReport.content as unknown as string }} />
            </div>
          </div>
        )}

        {/* Call to Action */}
        <div className="text-center py-24 border-t border-zinc-800 mt-24">
          <h2 className="text-3xl font-bold mb-6">Interested in this startup?</h2>
          <p className="text-zinc-400 text-lg mb-8 max-w-2xl mx-auto">
            This startup idea was generated and validated entirely by AI agents using the AI Start-up Incubator Simulator.
          </p>
          <a href="/" className="inline-flex items-center justify-center px-8 py-4 text-sm font-semibold rounded-full bg-white text-black hover:bg-zinc-200 transition-colors">
            Build your own AI Startup
          </a>
        </div>
      </div>
    </div>
  );
}
