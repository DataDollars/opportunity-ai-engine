"use client";

import { useState, useEffect } from "react";

interface Source {
  id: string;
  name: string;
  url: string;
  country: string;
  category: string;
  method: string;
  priority: number;
  active: boolean;
  last_scraped_at?: number;
}

interface Opportunity {
  id: string;
  name: string;
  description?: string;
  category: string;
  country: string;
  state?: string;
  industry: string[];
  eligibility?: string;
  benefits?: string;
  deadline?: string;
  documents: string[];
  apply_url?: string;
  last_updated: number;
  active_status: string;
  ministry?: string;
  target_users?: string[];
  business_stage?: string[];
  financial_amount?: string;
  application_process?: string;
  tags?: string[];
}

interface MatchResult {
  opportunity_id: string;
  opportunity_name: string;
  category: string;
  state?: string;
  benefits?: string;
  documents: string[];
  apply_url?: string;
  match_score: number;
  match_reason: string;
  missing_requirements: string[];
}

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "registry" | "sources">("dashboard");
  
  // Data States
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [matches, setMatches] = useState<MatchResult[]>([]);
  
  // Loading & Action States
  const [loadingOpps, setLoadingOpps] = useState(true);
  const [loadingSources, setLoadingSources] = useState(true);
  const [matchingLoading, setMatchingLoading] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncLogText, setSyncLogText] = useState<string | null>(null);
  
  // Profile Form States
  const [companyName, setCompanyName] = useState("Acme Food Industries");
  const [industry, setIndustry] = useState("Food Processing");
  const [stateFilter, setStateFilter] = useState("Maharashtra");
  const [employees, setEmployees] = useState(25);
  const [turnover, setTurnover] = useState(30000000); // 3 Cr
  const [businessType, setBusinessType] = useState("MSME");
  
  // Filters
  const [registrySearch, setRegistrySearch] = useState("");
  const [registryState, setRegistryState] = useState("");
  const [registryIndustry, setRegistryIndustry] = useState("");
  const [selectedOpp, setSelectedOpp] = useState<Opportunity | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch initial data
  const fetchOpportunities = async () => {
    try {
      setLoadingOpps(true);
      const res = await fetch(`${API_URL}/opportunities`);
      if (res.ok) {
        const data = await res.json();
        setOpportunities(data);
      }
    } catch (e) {
      console.error("Failed to load opportunities:", e);
    } finally {
      setLoadingOpps(false);
    }
  };

  const fetchSources = async () => {
    try {
      setLoadingSources(true);
      const res = await fetch(`${API_URL}/sources`);
      if (res.ok) {
        const data = await res.json();
        setSources(data);
      }
    } catch (e) {
      console.error("Failed to load sources:", e);
    } finally {
      setLoadingSources(false);
    }
  };

  useEffect(() => {
    fetchOpportunities();
    fetchSources();
  }, []);

  // Trigger sync manually
  const triggerSync = async () => {
    try {
      setSyncLoading(true);
      setSyncLogText("Initializing crawler sync pipeline...");
      
      const res = await fetch(`${API_URL}/sync?dry_run=false`, {
        method: "POST"
      });
      
      if (res.ok) {
        const data = await res.json();
        setSyncLogText(
          `Sync Completed Successfully!\n` +
          `------------------------------\n` +
          `• Sources Scraped: ${data.results.sources_scraped}\n` +
          `• Raw Docs Scraped: ${data.results.raw_docs_scraped}\n` +
          `• New Docs Saved: ${data.results.new_raw_docs_saved}\n` +
          `• Opportunities Processed: ${data.results.opportunities_processed}\n` +
          (data.results.errors.length > 0 ? `• Errors: ${data.results.errors.join("\n")}` : "")
        );
        fetchOpportunities();
        fetchSources();
      } else {
        setSyncLogText("Error: Sync pipeline execution failed on backend.");
      }
    } catch (err: any) {
      setSyncLogText(`Network Error: Could not connect to API.\n${err.message}`);
    } finally {
      setSyncLoading(false);
    }
  };

  // Run Profile Matching
  const runMatching = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setMatchingLoading(true);
      const res = await fetch(`${API_URL}/match`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          company_name: companyName,
          industry: industry,
          state: stateFilter,
          employees: Number(employees),
          turnover: Number(turnover),
          business_type: businessType
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        setMatches(data.matches || []);
      } else {
        console.error("Match API returned error code");
      }
    } catch (err) {
      console.error("Connection error running matching:", err);
    } finally {
      setMatchingLoading(false);
    }
  };

  // Filtered Registry List
  const filteredOpps = opportunities.filter((opp) => {
    const matchesSearch = opp.name.toLowerCase().includes(registrySearch.toLowerCase()) || 
                          (opp.description && opp.description.toLowerCase().includes(registrySearch.toLowerCase()));
    
    const matchesState = !registryState || (opp.state && opp.state.toLowerCase() === registryState.toLowerCase());
    
    const matchesIndustry = !registryIndustry || opp.industry.some(
      (ind) => ind.toLowerCase().includes(registryIndustry.toLowerCase()) || registryIndustry.toLowerCase().includes(ind.toLowerCase())
    );

    return matchesSearch && matchesState && matchesIndustry;
  });

  return (
    <main className="relative flex-1 p-4 md:p-8 overflow-y-auto z-10 font-sans">
      <div className="bg-grid-glow" />

      {/* Header Container */}
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold font-heading gradient-text tracking-tight">
            OPPORTUNITY AI
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            CTO Data Intelligence Engine for MSMEs and Grants Tracking
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`px-4 py-2 text-sm rounded-lg border transition-all ${
              activeTab === "dashboard"
                ? "bg-glow-violet/20 border-glow-violet text-white"
                : "border-white/10 hover:border-white/20 text-slate-400"
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab("registry")}
            className={`px-4 py-2 text-sm rounded-lg border transition-all ${
              activeTab === "registry"
                ? "bg-glow-violet/20 border-glow-violet text-white"
                : "border-white/10 hover:border-white/20 text-slate-400"
            }`}
          >
            Scheme Registry
          </button>
          <button
            onClick={() => setActiveTab("sources")}
            className={`px-4 py-2 text-sm rounded-lg border transition-all ${
              activeTab === "sources"
                ? "bg-glow-violet/20 border-glow-violet text-white"
                : "border-white/10 hover:border-white/20 text-slate-400"
            }`}
          >
            Data Sources
          </button>
        </div>
      </div>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto">
        
        {/* Metric Cards Banner */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="glass-card p-6 rounded-2xl">
            <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Total Schemes Tracked</p>
            <h3 className="text-2xl font-bold font-heading text-white mt-1">{loadingOpps ? "Loading..." : opportunities.length}</h3>
          </div>
          <div className="glass-card p-6 rounded-2xl">
            <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Active Scraper Sources</p>
            <h3 className="text-2xl font-bold font-heading text-white mt-1">{loadingSources ? "Loading..." : sources.length}</h3>
          </div>
          <div className="glass-card p-6 rounded-2xl">
            <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Matched Recommendations</p>
            <h3 className="text-2xl font-bold font-heading text-white mt-1">{matches.length}</h3>
          </div>
          <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Crawler Status</p>
                <h3 className="text-sm font-semibold text-brand-green mt-1">Live Pipeline</h3>
              </div>
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-green opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-brand-green"></span>
              </span>
            </div>
            <button
              onClick={triggerSync}
              disabled={syncLoading}
              className={`w-full text-center mt-3 text-xs py-1.5 rounded-lg font-semibold transition-all ${
                syncLoading
                  ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                  : "bg-glow-cyan/20 border border-glow-cyan/50 hover:bg-glow-cyan/30 text-white"
              }`}
            >
              {syncLoading ? "Syncing..." : "Sync Crawler Now"}
            </button>
          </div>
        </div>

        {/* Sync Console Logs Panel */}
        {syncLogText && (
          <div className="glass-card p-4 rounded-xl border-cyan-500/20 shadow-cyan-500/5 mb-8 font-mono text-xs text-cyan-400">
            <div className="flex justify-between items-center mb-2 border-b border-white/5 pb-2">
              <span className="font-semibold uppercase tracking-wider text-cyan-300">Pipeline execution console</span>
              <button 
                onClick={() => setSyncLogText(null)} 
                className="text-slate-400 hover:text-white"
              >
                ✕ Close Console
              </button>
            </div>
            <pre className="whitespace-pre-wrap">{syncLogText}</pre>
          </div>
        )}

        {/* Dynamic Content Views */}
        {activeTab === "dashboard" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            
            {/* Left Column: Form Setup */}
            <div className="lg:col-span-4 glass-card p-6 rounded-2xl">
              <h2 className="text-xl font-bold font-heading text-white mb-6 border-b border-white/5 pb-2">
                Company Profile
              </h2>
              
              <form onSubmit={runMatching} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase">Company Name</label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    required
                    className="w-full px-3 py-2 text-sm rounded-lg glass-input"
                    placeholder="Enter company name"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase">HQ Location (State)</label>
                  <select
                    value={stateFilter}
                    onChange={(e) => setStateFilter(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg glass-input cursor-pointer"
                  >
                    <option value="Maharashtra">Maharashtra</option>
                    <option value="Karnataka">Karnataka</option>
                    <option value="Gujarat">Gujarat</option>
                    <option value="Delhi">Delhi</option>
                    <option value="Tamil Nadu">Tamil Nadu</option>
                    <option value="Telangana">Telangana</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase">Sector/Industry</label>
                  <select
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg glass-input cursor-pointer"
                  >
                    <option value="Food Processing">Food Processing</option>
                    <option value="Textiles">Textiles</option>
                    <option value="Technology">Technology</option>
                    <option value="Manufacturing">Manufacturing</option>
                    <option value="Agriculture">Agriculture</option>
                    <option value="Export">Export</option>
                    <option value="Finance">Finance</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase">Employees</label>
                    <input
                      type="number"
                      value={employees}
                      onChange={(e) => setEmployees(Number(e.target.value))}
                      required
                      min={1}
                      className="w-full px-3 py-2 text-sm rounded-lg glass-input"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase">Turnover (INR)</label>
                    <input
                      type="number"
                      value={turnover}
                      onChange={(e) => setTurnover(Number(e.target.value))}
                      required
                      min={0}
                      className="w-full px-3 py-2 text-sm rounded-lg glass-input"
                      placeholder="e.g. 30000000"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase">Registration Profile</label>
                  <select
                    value={businessType}
                    onChange={(e) => setBusinessType(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg glass-input cursor-pointer"
                  >
                    <option value="MSME">MSME</option>
                    <option value="Startup">Startup</option>
                    <option value="Partnership">Partnership</option>
                    <option value="Sole Proprietorship">Sole Proprietorship</option>
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={matchingLoading}
                  className={`w-full py-2.5 rounded-lg text-sm font-semibold tracking-wider transition-all mt-4 ${
                    matchingLoading
                      ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                      : "bg-gradient-to-r from-glow-violet to-glow-cyan text-white hover:opacity-90 shadow-lg shadow-violet-500/10"
                  }`}
                >
                  {matchingLoading ? "Matching with Gemini AI..." : "Evaluate Eligibility"}
                </button>
              </form>
            </div>

            {/* Right Column: Recommendations */}
            <div className="lg:col-span-8 space-y-6">
              <h2 className="text-xl font-bold font-heading text-white border-b border-white/5 pb-2">
                Matching Recommendations
              </h2>

              {matchingLoading && (
                <div className="glass-card p-12 text-center rounded-2xl flex flex-col items-center justify-center space-y-4">
                  <span className="w-10 h-10 border-4 border-glow-violet border-t-transparent animate-spin rounded-full"></span>
                  <p className="text-slate-400 text-sm">Evaluating criteria metrics with LLM heuristics...</p>
                </div>
              )}

              {!matchingLoading && matches.length === 0 && (
                <div className="glass-card p-12 text-center rounded-2xl text-slate-400 text-sm">
                  No company profile submitted. Enter details on the left to verify real-time matches.
                </div>
              )}

              {!matchingLoading && matches.map((match) => (
                <div key={match.opportunity_id} className="glass-card p-6 rounded-2xl flex flex-col md:flex-row gap-6 items-start">
                  
                  {/* Score badge */}
                  <div className="flex-shrink-0 flex flex-col items-center">
                    <div className={`w-16 h-16 rounded-full flex items-center justify-center border-2 font-bold text-lg ${
                      match.match_score >= 75
                        ? "border-brand-green/80 text-brand-green bg-brand-green/10"
                        : match.match_score >= 50
                        ? "border-amber-500/80 text-amber-500 bg-amber-500/10"
                        : "border-red-500/80 text-red-500 bg-red-500/10"
                    }`}>
                      {match.match_score}%
                    </div>
                    <span className="text-[10px] text-slate-400 font-semibold mt-2 uppercase tracking-wide">Match Score</span>
                  </div>

                  {/* Scheme Text */}
                  <div className="flex-1 space-y-3">
                    <div>
                      <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider bg-white/5 text-slate-300">
                        {match.category.replace("_", " ")}
                      </span>
                      {match.state && (
                        <span className="ml-2 px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider bg-cyan-500/10 text-cyan-400">
                          {match.state}
                        </span>
                      )}
                      <h3 className="text-lg font-bold text-white mt-1.5">{match.opportunity_name}</h3>
                    </div>

                    <p className="text-slate-300 text-sm leading-relaxed">{match.match_reason}</p>

                    {match.benefits && (
                      <div className="text-xs bg-white/3 p-3 rounded-lg border border-white/5">
                        <span className="font-semibold text-slate-300 block mb-1">Subsidies/Benefits Available:</span>
                        <span className="text-slate-400 leading-relaxed">{match.benefits}</span>
                      </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                      {/* Documents Checklist */}
                      <div>
                        <span className="text-xs font-semibold text-slate-300 block mb-1.5">Required Documents:</span>
                        <ul className="text-xs text-slate-400 space-y-1">
                          {match.documents.map((doc, idx) => (
                            <li key={idx} className="flex items-center gap-1.5">
                              <span className="text-brand-green font-bold">✓</span> {doc}
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* Missing requirements */}
                      {match.missing_requirements.length > 0 && (
                        <div>
                          <span className="text-xs font-semibold text-amber-400 block mb-1.5">Check / Missing details:</span>
                          <ul className="text-xs text-amber-500/80 space-y-1">
                            {match.missing_requirements.map((req, idx) => (
                              <li key={idx} className="flex items-start gap-1.5">
                                <span className="font-bold">•</span> {req}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                    
                    {match.apply_url && (
                      <div className="pt-2">
                        <a
                          href={match.apply_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-block px-4 py-1.5 text-xs font-semibold bg-glow-violet/20 border border-glow-violet/50 rounded-lg text-white hover:bg-glow-violet/30 transition-all"
                        >
                          Apply on Official Portal ↗
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

          </div>
        )}

        {/* Opportunities Registry View */}
        {activeTab === "registry" && (
          <div className="glass-card p-6 rounded-2xl">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/5 pb-4 mb-6">
              <h2 className="text-xl font-bold font-heading text-white">Government Opportunity Register</h2>
              
              {/* Filters */}
              <div className="flex flex-wrap gap-2 w-full md:w-auto">
                <input
                  type="text"
                  value={registrySearch}
                  onChange={(e) => setRegistrySearch(e.target.value)}
                  placeholder="Search scheme name or desc..."
                  className="px-3 py-1.5 text-xs rounded-lg glass-input w-full sm:w-48"
                />
                <select
                  value={registryState}
                  onChange={(e) => setRegistryState(e.target.value)}
                  className="px-3 py-1.5 text-xs rounded-lg glass-input cursor-pointer"
                >
                  <option value="">All States</option>
                  <option value="Maharashtra">Maharashtra</option>
                  <option value="Karnataka">Karnataka</option>
                  <option value="Gujarat">Gujarat</option>
                  <option value="Delhi">Delhi</option>
                </select>
                <select
                  value={registryIndustry}
                  onChange={(e) => setRegistryIndustry(e.target.value)}
                  className="px-3 py-1.5 text-xs rounded-lg glass-input cursor-pointer"
                >
                  <option value="">All Industries</option>
                  <option value="Food Processing">Food Processing</option>
                  <option value="Textiles">Textiles</option>
                  <option value="Technology">Technology</option>
                  <option value="Manufacturing">Manufacturing</option>
                </select>
              </div>
            </div>

            {loadingOpps ? (
              <div className="text-center p-12 text-slate-400">Loading scheme databases...</div>
            ) : filteredOpps.length === 0 ? (
              <div className="text-center p-12 text-slate-400">No schemes found matching search criteria.</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredOpps.map((opp) => (
                  <div key={opp.id} className="glass-card p-5 rounded-xl flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start gap-2 mb-3">
                        <span className="px-2 py-0.5 rounded text-[9px] uppercase font-bold bg-white/5 text-slate-300">
                          {opp.category.replace("_", " ")}
                        </span>
                        {opp.state && (
                          <span className="px-2 py-0.5 rounded text-[9px] uppercase font-bold bg-cyan-500/10 text-cyan-400">
                            {opp.state}
                          </span>
                        )}
                      </div>
                      <h4 className="text-sm font-bold text-white mb-2">{opp.name}</h4>
                      <p className="text-xs text-slate-400 line-clamp-3 mb-4 leading-relaxed">
                        {opp.benefits || opp.eligibility || "No details provided"}
                      </p>
                    </div>

                    <div className="flex justify-between items-center border-t border-white/5 pt-3 mt-2">
                      <span className="text-[10px] text-slate-500">
                        Updated {new Date(opp.last_updated * 1000).toLocaleDateString()}
                      </span>
                      <button
                        onClick={() => setSelectedOpp(opp)}
                        className="text-xs text-glow-cyan hover:underline font-semibold"
                      >
                        Read Details →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Data Sources View */}
        {activeTab === "sources" && (
          <div className="glass-card p-6 rounded-2xl">
            <h2 className="text-xl font-bold font-heading text-white border-b border-white/5 pb-4 mb-6">
              Opportunity Sources Index
            </h2>

            {loadingSources ? (
              <div className="text-center p-12 text-slate-400">Loading pipeline crawlers index...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-white/5 text-slate-400 uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="p-3">Portal Name</th>
                      <th className="p-3">URL</th>
                      <th className="p-3">Method</th>
                      <th className="p-3">Priority</th>
                      <th className="p-3">Last Synced</th>
                      <th className="p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {sources.map((src) => (
                      <tr key={src.id} className="hover:bg-white/2 transition-colors">
                        <td className="p-3 font-semibold text-white">{src.name}</td>
                        <td className="p-3">
                          <a href={src.url} target="_blank" rel="noopener noreferrer" className="text-glow-cyan hover:underline">
                            {src.url}
                          </a>
                        </td>
                        <td className="p-3 uppercase">{src.method}</td>
                        <td className="p-3">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                            src.priority === 1 ? "bg-red-500/10 text-red-400" : src.priority === 2 ? "bg-amber-500/10 text-amber-400" : "bg-slate-500/20 text-slate-400"
                          }`}>
                            P{src.priority}
                          </span>
                        </td>
                        <td className="p-3 text-slate-400">
                          {src.last_scraped_at 
                            ? new Date(src.last_scraped_at * 1000).toLocaleString()
                            : "Never Synced"}
                        </td>
                        <td className="p-3">
                          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-semibold ${
                            src.active ? "bg-brand-green/10 text-brand-green" : "bg-red-500/10 text-red-400"
                          }`}>
                            <span className={`w-1 h-1 rounded-full ${src.active ? "bg-brand-green" : "bg-red-400"}`} />
                            {src.active ? "Active" : "Disabled"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Opportunity Details Modal */}
      {selectedOpp && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card max-w-2xl w-full max-h-[85vh] overflow-y-auto rounded-2xl p-6 relative">
            <button
              onClick={() => setSelectedOpp(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white text-lg"
            >
              ✕
            </button>

            <div className="border-b border-white/5 pb-4 mb-4">
              <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-white/5 text-slate-300">
                {selectedOpp.category.replace("_", " ")}
              </span>
              {selectedOpp.state && (
                <span className="ml-2 px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-cyan-500/10 text-cyan-400">
                  {selectedOpp.state}
                </span>
              )}
              <h3 className="text-xl font-bold text-white mt-2">{selectedOpp.name}</h3>
              {selectedOpp.ministry && (
                <p className="text-xs text-slate-400 mt-1">{selectedOpp.ministry}</p>
              )}
            </div>

            <div className="space-y-4 text-sm text-slate-300 leading-relaxed">
              <div>
                <h5 className="text-xs uppercase font-bold text-slate-400 mb-1">Overview</h5>
                <p>{selectedOpp.eligibility || "No criteria provided"}</p>
              </div>

              {selectedOpp.benefits && (
                <div>
                  <h5 className="text-xs uppercase font-bold text-slate-400 mb-1">Financial Subsidy / Benefits</h5>
                  <p className="text-slate-200">{selectedOpp.benefits}</p>
                </div>
              )}

              {selectedOpp.application_process && (
                <div>
                  <h5 className="text-xs uppercase font-bold text-slate-400 mb-1">Application Steps</h5>
                  <p>{selectedOpp.application_process}</p>
                </div>
              )}

              {selectedOpp.documents.length > 0 && (
                <div>
                  <h5 className="text-xs uppercase font-bold text-slate-400 mb-1">Required Documents</h5>
                  <ul className="list-disc pl-5 space-y-1 text-slate-400">
                    {selectedOpp.documents.map((doc, idx) => (
                      <li key={idx}>{doc}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 border-t border-white/5 pt-4 text-xs text-slate-400">
                <div>
                  <span className="font-semibold text-slate-300 block">Deadline:</span>
                  {selectedOpp.deadline || "Rolling submissions"}
                </div>
                <div>
                  <span className="font-semibold text-slate-300 block">Eligible Sectors:</span>
                  {selectedOpp.industry.join(", ")}
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t border-white/5 pt-4 mt-6">
              <button
                onClick={() => setSelectedOpp(null)}
                className="px-4 py-2 text-xs rounded-lg border border-white/10 hover:border-white/20 text-slate-400 hover:text-white"
              >
                Close
              </button>
              {selectedOpp.apply_url && (
                <a
                  href={selectedOpp.apply_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 text-xs font-semibold bg-gradient-to-r from-glow-violet to-glow-cyan rounded-lg text-white"
                >
                  Visit Portal ↗
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
