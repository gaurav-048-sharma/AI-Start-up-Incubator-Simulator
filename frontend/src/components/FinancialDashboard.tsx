"use client";

import React, { useMemo } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface FinancialDashboardProps {
  content: string;
}

interface FinancialData {
  month: string;
  revenue: number;
  cost: number;
  users: number;
}

export function FinancialDashboard({ content }: FinancialDashboardProps) {
  // Extract JSON from markdown
  const { jsonStr, strippedContent } = useMemo(() => {
    const jsonMatch = content.match(/```json\s*([\s\S]*?)\s*```/);
    if (jsonMatch && jsonMatch[1]) {
      return {
        jsonStr: jsonMatch[1],
        strippedContent: content.replace(jsonMatch[0], ""),
      };
    }
    return { jsonStr: null, strippedContent: content };
  }, [content]);

  const data: FinancialData[] = useMemo(() => {
    if (!jsonStr) return [];
    try {
      return JSON.parse(jsonStr) as FinancialData[];
    } catch (e) {
      console.error("Failed to parse financial JSON data", e);
      return [];
    }
  }, [jsonStr]);

  if (!data || data.length === 0) {
    return (
      <div className="prose prose-invert max-w-none">
        <div dangerouslySetInnerHTML={{ __html: content }} />
      </div>
    );
  }

  // Calculate some derived metrics
  const totalRevenue = data.reduce((sum, d) => sum + d.revenue, 0);
  const totalCost = data.reduce((sum, d) => sum + d.cost, 0);
  const breakEvenMonth = data.find(d => d.revenue >= d.cost)?.month || "N/A";
  const finalUsers = data[data.length - 1]?.users || 0;

  return (
    <div className="space-y-12">
      {/* Top Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <p className="text-zinc-400 text-sm font-medium mb-1">Total Year 1 Revenue</p>
          <p className="text-3xl font-bold text-white">${totalRevenue.toLocaleString()}</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <p className="text-zinc-400 text-sm font-medium mb-1">Total Year 1 Cost</p>
          <p className="text-3xl font-bold text-red-400">${totalCost.toLocaleString()}</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <p className="text-zinc-400 text-sm font-medium mb-1">Break-even Point</p>
          <p className="text-3xl font-bold text-emerald-400">{breakEvenMonth}</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <p className="text-zinc-400 text-sm font-medium mb-1">Projected Users (Mo 12)</p>
          <p className="text-3xl font-bold text-blue-400">{finalUsers.toLocaleString()}</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Revenue vs Cost */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h3 className="text-lg font-medium text-white mb-6">Revenue vs Cost</h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                <XAxis dataKey="month" stroke="#888" tick={{ fill: "#888", fontSize: 12 }} />
                <YAxis stroke="#888" tick={{ fill: "#888", fontSize: 12 }} tickFormatter={(value) => `$${value/1000}k`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", borderRadius: "8px" }}
                  itemStyle={{ color: "#fff" }}
                  formatter={(value: number) => [`$${value.toLocaleString()}`, ""]}
                />
                <Legend />
                <Line type="monotone" dataKey="revenue" name="Revenue" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey="cost" name="Cost" stroke="#f87171" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* User Growth */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h3 className="text-lg font-medium text-white mb-6">User Growth</h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                <XAxis dataKey="month" stroke="#888" tick={{ fill: "#888", fontSize: 12 }} />
                <YAxis stroke="#888" tick={{ fill: "#888", fontSize: 12 }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", borderRadius: "8px" }}
                  itemStyle={{ color: "#fff" }}
                  formatter={(value: number) => [value.toLocaleString(), "Users"]}
                />
                <Legend />
                <Bar dataKey="users" name="Active Users" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* The rest of the Markdown Report */}
      <div className="mt-12 bg-zinc-900/50 border border-zinc-800 rounded-xl p-8">
        <h3 className="text-xl font-medium text-white mb-6 border-b border-zinc-800 pb-4">Financial Analyst Report</h3>
        <div className="prose prose-invert prose-emerald max-w-none">
          <div dangerouslySetInnerHTML={{ __html: strippedContent }} />
        </div>
      </div>
    </div>
  );
}
