import React, { useState, useEffect, useRef } from 'react';
import { Upload, MessageSquare, FileText, Menu, X, Play, CheckCircle, Download, File, Calendar, AlertTriangle, Clock, Archive, Trash2, RefreshCw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { JsonView, darkStyles, defaultStyles } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';
import './index.css';

// --- Components ---

const Button = ({ children, onClick, variant = 'primary', className = '', disabled = false, ...props }) => {
  const baseStyle = "px-4 py-2 rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 flex items-center justify-center gap-2";
  const variants = {
    primary: "bg-[hsl(var(--brand-blue))] text-white hover:bg-blue-700 focus:ring-blue-500",
    secondary: "bg-gray-100 text-gray-900 hover:bg-gray-200 focus:ring-gray-400",
    outline: "border border-gray-300 text-gray-700 hover:bg-gray-50",
    ghost: "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
  };
  
  return (
    <button 
      className={`${baseStyle} ${variants[variant]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
      onClick={onClick}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
};

const Card = ({ children, className = '' }) => (
  <div className={`bg-white rounded-lg border border-gray-200 shadow-sm ${className}`}>
    {children}
  </div>
);

const Tabs = ({ activeTab, setActiveTab, tabs }) => (
  <div className="flex border-b border-gray-200">
    {tabs.map(tab => (
      <button
        key={tab.id}
        onClick={() => setActiveTab(tab.id)}
        className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
          activeTab === tab.id
            ? 'border-[hsl(var(--brand-blue))] text-[hsl(var(--brand-blue))]'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
        }`}
      >
        {tab.label}
      </button>
    ))}
  </div>
);

const SummaryView = ({ data }) => {
    if (!data) return null;

    const fields = [
        { key: "project_name", label: "Project Name" },
        { key: "general_contractor", label: "General Contractor" },
        { key: "owner", label: "Owner" },
        { key: "architect", label: "Architect" },
        { key: "project_address", label: "Project Address" },
        { key: "total_contract_value", label: "Total Contract Value" },
        { key: "project_start_date", label: "Start Date" },
        { key: "project_substantial_completion", label: "Substantial Completion" },
        { key: "payment_terms", label: "Payment Terms" },
        { key: "retention_percent", label: "Retention %" },
        { key: "prevailing_wage", label: "Prevailing Wage" },
        { key: "tax_status", label: "Tax Rate / Exempt" },
        { key: "parking", label: "Parking" },
        { key: "ocip_ccip_status", label: "OCIP / CCIP" },
        { key: "insurance_compliance", label: "Insurance Compliance" }
    ];

    return (
        <div className="space-y-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Project Summary</h2>
            <div className="grid grid-cols-1 gap-4">
                {fields.map((field) => {
                    const value = data[field.key];
                    let valueClass = "text-gray-900";
                    let containerClass = "bg-white p-4 rounded border border-gray-200";

                    // Special styling for Insurance Compliance
                    if (field.key === "insurance_compliance") {
                        if (value?.includes("Not Compliant")) {
                            valueClass = "text-red-700 font-bold";
                            containerClass = "bg-red-50 p-4 rounded border border-red-200";
                        } else if (value?.includes("Compliant")) {
                            valueClass = "text-green-700 font-bold";
                            containerClass = "bg-green-50 p-4 rounded border border-green-200";
                        } else if (value?.includes("Cannot Be Confirmed")) {
                            valueClass = "text-yellow-700 font-bold";
                            containerClass = "bg-yellow-50 p-4 rounded border border-yellow-200";
                        }
                    }

                    // Special styling for Parking
                    if (field.key === "parking") {
                        if (value?.toLowerCase().includes("fee-based") || value?.toLowerCase().includes("subcontractor responsible")) {
                            valueClass = "text-yellow-700 font-semibold";
                            containerClass = "bg-yellow-50 p-4 rounded border border-yellow-200";
                        } else if (value?.toLowerCase().includes("included") || value?.toLowerCase().includes("provided") || value?.toLowerCase().includes("no cost")) {
                            valueClass = "text-green-700 font-semibold";
                            containerClass = "bg-green-50 p-4 rounded border border-green-200";
                        } else if (value?.toLowerCase().includes("not specified")) {
                            valueClass = "text-gray-500 italic";
                        }
                    }

                    // Special styling for Prevailing Wage
                    if (field.key === "prevailing_wage") {
                        if (value?.toLowerCase() === "yes") {
                            valueClass = "text-blue-700 font-semibold";
                            containerClass = "bg-blue-50 p-4 rounded border border-blue-200";
                        }
                    }

                    // Special styling for OCIP/CCIP
                    if (field.key === "ocip_ccip_status") {
                        if (value?.toLowerCase().startsWith("yes")) {
                            valueClass = "text-blue-700 font-semibold";
                            containerClass = "bg-blue-50 p-4 rounded border border-blue-200";
                        }
                    }

                    return (
                        <div key={field.key} className={containerClass}>
                            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1 font-semibold">
                                {field.label}
                            </div>
                            <div className={`text-sm ${valueClass}`}>
                                {value || "Not identified"}
                            </div>
                            {/* Show Insurance details if not compliant */}
                            {field.key === "insurance_compliance" && data.insurance_notes && (
                                <div className="mt-2 text-xs text-gray-600 border-t border-gray-200 pt-2">
                                    {data.insurance_notes}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

const NegotiationView = ({ data }) => {
    if (!data) return null;

    return (
        <div className="space-y-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Negotiation Summary</h2>
            <div className="space-y-4">
                {data.map((item, idx) => (
                    <Card key={idx} className="overflow-hidden border border-gray-200">
                        <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex justify-between items-center">
                            <div className="flex flex-col">
                                <span className="font-bold text-gray-900">{idx + 1}. {item.title}</span>
                                <span className="text-xs text-gray-500 font-mono">{item.clause_reference}</span>
                            </div>
                            <span className={`px-2 py-1 rounded text-xs font-bold ${
                                item.action === 'Strike' ? 'bg-red-100 text-red-700' :
                                item.action === 'Modify' ? 'bg-blue-100 text-blue-700' :
                                'bg-yellow-100 text-yellow-700'
                            }`}>
                                {item.action}
                            </span>
                        </div>
                        <div className="p-4 space-y-4">
                            <div>
                                <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Current Language</div>
                                <div className="bg-white p-3 rounded border border-gray-200 text-sm text-gray-600 italic font-mono">
                                    "{item.verbatim_text}"
                                </div>
                            </div>
                            
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <div className="text-xs text-blue-600 uppercase tracking-wide mb-1 font-semibold">Proposed Change</div>
                                    <div className="bg-blue-50 p-3 rounded text-sm text-blue-900 font-medium">
                                        {item.proposal_text}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Reasoning</div>
                                    <div className="text-sm text-gray-700">
                                        {item.reason}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </Card>
                ))}
            </div>
        </div>
    );
};

// Scope View Component - Proposal-driven scope comparison
const ScopeView = ({ data }) => {
    if (!data) return null;

    const getStatusColor = (status) => {
        if (!status) return "bg-gray-100 text-gray-600";
        if (status.includes("Aligned") && !status.includes("Not Aligned")) {
            return "bg-green-100 text-green-700";
        }
        if (status.includes("Not Aligned") || status.includes("Corrections Required")) {
            return "bg-red-100 text-red-700";
        }
        if (status.includes("Pending")) {
            return "bg-yellow-100 text-yellow-700";
        }
        return "bg-gray-100 text-gray-600";
    };

    const getResultColor = (result) => {
        if (result === "Aligned") return "bg-green-100 text-green-700";
        if (result === "Discrepancy Identified") return "bg-red-100 text-red-700";
        return "bg-yellow-100 text-yellow-700";
    };

    const getCategoryColor = (category) => {
        const colors = {
            "Added Scope": "bg-red-100 text-red-700",
            "Expanded Scope": "bg-orange-100 text-orange-700",
            "Missing Scope": "bg-purple-100 text-purple-700",
            "Responsibility Shift": "bg-blue-100 text-blue-700",
            "Technical Change": "bg-indigo-100 text-indigo-700",
            "Specification Conflict": "bg-pink-100 text-pink-700"
        };
        return colors[category] || "bg-gray-100 text-gray-600";
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-bold text-gray-900">Scope Review</h2>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${getStatusColor(data.scope_review_status)}`}>
                    {data.scope_review_status || "Pending"}
                </span>
            </div>

            {/* Review Mode Info */}
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span className="text-gray-500">Review Mode:</span>
                        <span className="ml-2 font-medium text-gray-900">
                            {data.scope_review_mode === "proposal_only" ? "Proposal Only" : "Proposal + Contract"}
                        </span>
                    </div>
                    <div>
                        <span className="text-gray-500">Proposal:</span>
                        <span className="ml-2 font-medium text-green-600">{data.proposal_filename || "Uploaded"}</span>
                    </div>
                    {data.contract_filename && (
                        <div className="col-span-2">
                            <span className="text-gray-500">Contract:</span>
                            <span className="ml-2 font-medium text-blue-600">{data.contract_filename}</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Scopes List */}
            <div className="space-y-4">
                {data.scopes_identified && data.scopes_identified.map((scope, idx) => (
                    <Card key={idx} className="overflow-hidden border border-gray-200">
                        <div className="bg-gray-50 px-4 py-3 border-b border-gray-200 flex justify-between items-center">
                            <span className="font-bold text-gray-900">{idx + 1}. {scope.scope_name}</span>
                            <span className={`px-2 py-1 rounded text-xs font-bold ${getResultColor(scope.review_result)}`}>
                                {scope.review_result}
                            </span>
                        </div>
                        
                        <div className="p-4 space-y-4">
                            {/* Proposal Details */}
                            <div className="space-y-3">
                                {scope.proposal_inclusions && scope.proposal_inclusions.length > 0 && (
                                    <div>
                                        <div className="text-xs text-green-600 uppercase tracking-wide mb-1 font-semibold">Inclusions</div>
                                        <ul className="list-disc list-inside text-sm text-gray-700 bg-green-50 p-2 rounded">
                                            {scope.proposal_inclusions.map((item, i) => <li key={i}>{item}</li>)}
                                        </ul>
                                    </div>
                                )}
                                
                                {scope.proposal_exclusions && scope.proposal_exclusions.length > 0 && (
                                    <div>
                                        <div className="text-xs text-red-600 uppercase tracking-wide mb-1 font-semibold">Exclusions</div>
                                        <ul className="list-disc list-inside text-sm text-gray-700 bg-red-50 p-2 rounded">
                                            {scope.proposal_exclusions.map((item, i) => <li key={i}>{item}</li>)}
                                        </ul>
                                    </div>
                                )}
                                
                                {scope.proposal_qualifications && scope.proposal_qualifications.length > 0 && (
                                    <div>
                                        <div className="text-xs text-yellow-600 uppercase tracking-wide mb-1 font-semibold">Qualifications</div>
                                        <ul className="list-disc list-inside text-sm text-gray-700 bg-yellow-50 p-2 rounded">
                                            {scope.proposal_qualifications.map((item, i) => <li key={i}>{item}</li>)}
                                        </ul>
                                    </div>
                                )}
                            </div>

                            {/* Contract Reference */}
                            {scope.contract_reference && (
                                <div>
                                    <div className="text-xs text-blue-600 uppercase tracking-wide mb-1 font-semibold">Contract Reference</div>
                                    <div className="bg-blue-50 p-3 rounded text-sm text-gray-700 italic">
                                        "{scope.contract_reference}"
                                    </div>
                                </div>
                            )}

                            {/* Discrepancy Details */}
                            {scope.review_result === "Discrepancy Identified" && (
                                <div className="border-t border-gray-200 pt-4 mt-4 space-y-3">
                                    <div className="flex items-center gap-2">
                                        <span className={`px-2 py-1 rounded text-xs font-bold ${getCategoryColor(scope.discrepancy_category)}`}>
                                            {scope.discrepancy_category}
                                        </span>
                                        {scope.abs_position && (
                                            <span className="px-2 py-1 rounded text-xs font-bold bg-red-600 text-white">
                                                {scope.abs_position}
                                            </span>
                                        )}
                                    </div>
                                    
                                    {scope.issue_description && (
                                        <div>
                                            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Issue Description</div>
                                            <div className="text-sm text-gray-700">{scope.issue_description}</div>
                                        </div>
                                    )}
                                    
                                    {scope.required_correction && (
                                        <div className="bg-red-50 p-3 rounded border border-red-200">
                                            <div className="text-xs text-red-600 uppercase tracking-wide mb-1 font-semibold">Required Correction</div>
                                            <div className="text-sm text-red-800 font-medium">{scope.required_correction}</div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </Card>
                ))}
            </div>

            {/* No Scopes Message */}
            {(!data.scopes_identified || data.scopes_identified.length === 0) && (
                <div className="text-center py-8 text-gray-500">
                    <p>No scopes identified yet.</p>
                    <p className="text-sm mt-2">Upload a Proposal document to begin scope review.</p>
                </div>
            )}

            {/* Final Status */}
            <div className={`p-4 rounded-lg ${getStatusColor(data.scope_review_status)}`}>
                <div className="font-bold text-center">
                    {data.scope_review_status || "Scope Review Status: Pending"}
                </div>
            </div>
        </div>
    );
};

// History View Component - View and load past contract reviews
const HistoryView = ({ reviews, onLoadReview, onDeleteReview, onRefresh, isLoading }) => {
    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { 
            year: 'numeric',
            month: 'short', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getRetentionColor = (daysRemaining) => {
        if (daysRemaining === null || daysRemaining === undefined) return "text-gray-400";
        if (daysRemaining <= 7) return "text-red-600";
        if (daysRemaining <= 30) return "text-yellow-600";
        return "text-green-600";
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-bold text-gray-900">Contract Review History</h2>
                    <p className="text-sm text-gray-500 mt-1">Reviews are retained for 90 days</p>
                </div>
                <button 
                    onClick={onRefresh}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                >
                    <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
                    Refresh
                </button>
            </div>

            {reviews.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                    <Archive size={48} className="mx-auto mb-4 opacity-50" />
                    <p className="text-lg">No contract reviews in history</p>
                    <p className="text-sm mt-2">Completed reviews will appear here</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {reviews.map((review) => (
                        <Card key={review.review_id} className="overflow-hidden hover:shadow-md transition-shadow">
                            <div className="p-4">
                                <div className="flex justify-between items-start">
                                    <div className="flex-1 min-w-0">
                                        <h3 className="font-semibold text-gray-900 truncate">
                                            {review.project_name || "Untitled Review"}
                                        </h3>
                                        <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                                            <span className="flex items-center gap-1">
                                                <Calendar size={12} />
                                                {formatDate(review.updated_at || review.created_at)}
                                            </span>
                                            <span className={`flex items-center gap-1 ${getRetentionColor(review.days_remaining)}`}>
                                                <Clock size={12} />
                                                {review.days_remaining !== null ? `${review.days_remaining} days left` : ""}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 ml-4">
                                        <button
                                            onClick={() => onLoadReview(review.review_id)}
                                            className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                                        >
                                            Load
                                        </button>
                                        <button
                                            onClick={() => onDeleteReview(review.review_id)}
                                            className="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                </div>
                                
                                {/* Status indicators */}
                                <div className="flex flex-wrap gap-2 mt-3">
                                    {review.contract_count > 0 && (
                                        <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">
                                            {review.contract_count} Contract{review.contract_count > 1 ? 's' : ''}
                                        </span>
                                    )}
                                    {review.proposal_count > 0 && (
                                        <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded">
                                            {review.proposal_count} Proposal{review.proposal_count > 1 ? 's' : ''}
                                        </span>
                                    )}
                                    {review.has_summary && (
                                        <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded">
                                            Summary
                                        </span>
                                    )}
                                    {review.has_terms && (
                                        <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-700 rounded">
                                            Terms
                                        </span>
                                    )}
                                    {review.has_scope && (
                                        <span className="px-2 py-0.5 text-xs bg-orange-100 text-orange-700 rounded">
                                            Scope
                                        </span>
                                    )}
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
};

// --- Main App ---

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState('chat');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [taskType, setTaskType] = useState("INITIAL_CONTRACT_REVIEW");
  
  // Document management state - filtered by current session
  const [contracts, setContracts] = useState([]);  // Contract documents for current session
  const [proposals, setProposals] = useState([]);  // Proposal documents for current session
  const [activeContract, setActiveContract] = useState(null);
  const [activeProposal, setActiveProposal] = useState(null);
  
  // History state
  const [reviewHistory, setReviewHistory] = useState([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [loadedReviewId, setLoadedReviewId] = useState(null);
  
  const messagesEndRef = useRef(null);
  const backendUrl = ""; // Use relative path for Ingress routing

  // Load documents for current session and history on mount
  useEffect(() => {
    createNewSession();
  }, []);

  // Load documents when sessionId changes
  useEffect(() => {
    if (sessionId) {
      loadDocuments(sessionId);
    }
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load history on mount
  useEffect(() => {
    loadHistory();
  }, []);

  const loadDocuments = async (sid) => {
    try {
      const url = sid ? `${backendUrl}/api/documents?session_id=${sid}` : `${backendUrl}/api/documents`;
      const res = await fetch(url);
      const docs = await res.json();
      
      const contractDocs = docs.filter(d => d.document_type === 'contract');
      const proposalDocs = docs.filter(d => d.document_type === 'proposal');
      
      setContracts(contractDocs);
      setProposals(proposalDocs);
      
      // Set active documents
      const activeC = contractDocs.find(d => d.is_active);
      const activeP = proposalDocs.find(d => d.is_active);
      setActiveContract(activeC || null);
      setActiveProposal(activeP || null);
    } catch (err) {
      console.error("Failed to load documents", err);
    }
  };

  const createNewSession = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_type: taskType })
      });
      const data = await res.json();
      setSessionId(data.session_id);
      setMessages([{ role: 'assistant', content: `Hello! I'm your ABS Contract Admin Agent. I'm ready to help you review documents for **${taskType.replace(/_/g, ' ')}**. Upload a contract to get started.` }]);
      setAnalysisResult(null);
      setLoadedReviewId(null);
      // Clear documents for new session
      setContracts([]);
      setProposals([]);
      setActiveContract(null);
      setActiveProposal(null);
    } catch (err) {
      console.error("Failed to create session", err);
    }
  };

  // History functions
  const loadHistory = async () => {
    setIsHistoryLoading(true);
    try {
      const res = await fetch(`${backendUrl}/api/contract-reviews?limit=50`);
      const data = await res.json();
      setReviewHistory(data.reviews || []);
    } catch (err) {
      console.error("Failed to load history", err);
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const saveCurrentReview = async () => {
    if (!sessionId) return;
    
    try {
      const res = await fetch(`${backendUrl}/api/contract-reviews`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          project_name: analysisResult?.structured_data?.summary_data?.project_name,
          messages: messages,
          summary_data: analysisResult?.structured_data?.summary_data,
          negotiation_summary: analysisResult?.structured_data?.negotiation_summary,
          scope_data: analysisResult?.structured_data?.scope_data,
          analysis_result: analysisResult
        })
      });
      const data = await res.json();
      console.log("Review saved:", data);
      // Refresh history
      loadHistory();
      return data;
    } catch (err) {
      console.error("Failed to save review", err);
    }
  };

  const loadReviewFromHistory = async (reviewId) => {
    try {
      const res = await fetch(`${backendUrl}/api/contract-reviews/${reviewId}`);
      const review = await res.json();
      
      // Load the review data into state
      setLoadedReviewId(reviewId);
      setMessages(review.messages || []);
      
      // Reconstruct analysis result
      if (review.summary_data || review.negotiation_summary || review.scope_data) {
        setAnalysisResult({
          structured_data: {
            summary_data: review.summary_data,
            negotiation_summary: review.negotiation_summary,
            scope_data: review.scope_data
          },
          ...review.analysis_result
        });
      }
      
      // Set task type if available
      if (review.task_type) {
        setTaskType(review.task_type);
      }
      
      // Load documents associated with the review
      setContracts(review.contracts || []);
      setProposals(review.proposals || []);
      
      // Set active documents
      const activeC = (review.contracts || []).find(d => d.is_active);
      const activeP = (review.proposals || []).find(d => d.is_active);
      setActiveContract(activeC || null);
      setActiveProposal(activeP || null);
      
      // Switch to chat tab
      setActiveTab('chat');
      
      // Show notification
      setMessages(prev => [...prev, { 
        role: 'system', 
        content: `Loaded contract review: **${review.project_name || 'Untitled'}** (${review.days_remaining} days remaining)` 
      }]);
      
    } catch (err) {
      console.error("Failed to load review", err);
    }
  };

  const deleteReviewFromHistory = async (reviewId) => {
    if (!confirm("Are you sure you want to delete this contract review?")) return;
    
    try {
      await fetch(`${backendUrl}/api/contract-reviews/${reviewId}`, {
        method: 'DELETE'
      });
      // Refresh history
      loadHistory();
    } catch (err) {
      console.error("Failed to delete review", err);
    }
  };

  // Auto-save review when analysis completes
  useEffect(() => {
    if (analysisResult && sessionId) {
      saveCurrentReview();
    }
  }, [analysisResult]);

  const [processingQueue, setProcessingQueue] = useState([]);
  const [processingStats, setProcessingStats] = useState({ completed: 0, total: 0 });
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState({ 
    stage: '', // 'uploading', 'extracting', 'analyzing', 'complete', 'error'
    filename: '',
    progress: 0,
    message: ''
  });

  useEffect(() => {
    if (processingQueue.length > 0 && !isProcessing) {
        processNextInQueue();
    }
  }, [processingQueue, isProcessing]);

  const processNextInQueue = async () => {
      setIsProcessing(true);
      const currentFile = processingQueue[0];
      const { file, taskType, documentType } = currentFile;

      // Update processing status (left pane only)
      setProcessingStatus({
        stage: 'uploading',
        filename: file.name,
        progress: 10,
        message: `Uploading ${file.name}...`
      });

      try {
          // 1. Upload with document type and session_id
          setProcessingStatus(prev => ({ ...prev, stage: 'uploading', progress: 20, message: `Uploading ${file.name}...` }));
          
          const formData = new FormData();
          formData.append('file', file);
          
          const uploadUrl = sessionId 
            ? `${backendUrl}/api/upload?document_type=${documentType}&session_id=${sessionId}`
            : `${backendUrl}/api/upload?document_type=${documentType}`;
          
          const uploadRes = await fetch(uploadUrl, {
              method: 'POST',
              body: formData
          });
          
          if (!uploadRes.ok) {
              const err = await uploadRes.json().catch(() => ({}));
              throw new Error(err.detail || `Upload failed: ${uploadRes.status}`);
          }
          
          setProcessingStatus(prev => ({ ...prev, stage: 'extracting', progress: 40, message: `Extracting text from ${file.name}...` }));
          
          const uploadData = await uploadRes.json();
          
          // Reload documents for current session
          await loadDocuments(sessionId);
          
          setProcessingStatus(prev => ({ ...prev, progress: 50, message: `Document uploaded successfully` }));

          // 2. Attach to session
          if (sessionId) {
              await fetch(`${backendUrl}/api/sessions/${sessionId}/attach`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ file_id: uploadData.file_id })
              });

              // 3. Analyze
              setProcessingStatus(prev => ({ ...prev, stage: 'analyzing', progress: 60, message: `Analyzing ${file.name} with AI...` }));
              await runAnalysis(uploadData.file_id, taskType, file.name);
              
              setProcessingStatus(prev => ({ ...prev, stage: 'complete', progress: 100, message: `Completed ${file.name}` }));
          }

      } catch (err) {
          console.error(`Error processing ${file.name}`, err);
          setProcessingStatus(prev => ({ ...prev, stage: 'error', progress: 0, message: err.message || 'Processing failed' }));
          // Only show error in chat
          setMessages(prev => [...prev, { role: 'assistant', content: `Error processing **${file.name}**: ${err.message || 'Please try again.'}` }]);
      } finally {
          // Cleanup
          setProcessingStats(prev => ({ ...prev, completed: prev.completed + 1 }));
          setProcessingQueue(prev => prev.slice(1));
          setIsProcessing(false);
          
          // Clear status after a delay if queue is empty
          if (processingQueue.length <= 1) {
            setTimeout(() => {
              setProcessingStatus({ stage: '', filename: '', progress: 0, message: '' });
            }, 2000);
          }
      }
  };

  // Handle Contract upload (from "Upload Contract" control)
  const handleContractUpload = (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (selectedFiles.length === 0) return;

    // Reset stats if starting a new batch from idle
    if (processingQueue.length === 0) {
        setProcessingStats({ completed: 0, total: selectedFiles.length });
    } else {
        setProcessingStats(prev => ({ ...prev, total: prev.total + selectedFiles.length }));
    }

    // Add to queue with document_type = "contract"
    const newQueueItems = selectedFiles.map(file => ({
        file,
        taskType,
        documentType: "contract"
    }));
    
    setProcessingQueue(prev => [...prev, ...newQueueItems]);
  };

  // Handle Proposal upload (from "Upload Proposal" control)
  const handleProposalUpload = (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (selectedFiles.length === 0) return;

    // Reset stats if starting a new batch from idle
    if (processingQueue.length === 0) {
        setProcessingStats({ completed: 0, total: selectedFiles.length });
    } else {
        setProcessingStats(prev => ({ ...prev, total: prev.total + selectedFiles.length }));
    }

    // Add to queue with document_type = "proposal"
    const newQueueItems = selectedFiles.map(file => ({
        file,
        taskType,
        documentType: "proposal"
    }));
    
    setProcessingQueue(prev => [...prev, ...newQueueItems]);
  };

  // Set a document as active
  const setDocumentActive = async (fileId, documentType) => {
    try {
      await fetch(`${backendUrl}/api/documents/set-active`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_id: fileId, document_type: documentType })
      });
      await loadDocuments();
      setMessages(prev => [...prev, { 
        role: 'system', 
        content: `Set ${documentType} as active.` 
      }]);
    } catch (err) {
      console.error("Failed to set active document", err);
    }
  };

  // Delete a document
  const deleteDocument = async (fileId, documentType) => {
    try {
      await fetch(`${backendUrl}/api/documents/${fileId}`, {
        method: 'DELETE'
      });
      await loadDocuments();
      setMessages(prev => [...prev, { 
        role: 'system', 
        content: `Deleted ${documentType} document.` 
      }]);
    } catch (err) {
      console.error("Failed to delete document", err);
    }
  };

  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const runAnalysis = async (fileId, type, filename, retries = 3) => {
    // Note: No setIsLoading(true) here because queue manages it
    
    for (let attempt = 0; attempt < retries; attempt++) {
        try {
            const payload = { file_id: fileId, task_type: type };

            const res = await fetch(`${backendUrl}/api/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (!res.ok) {
                // If it's a 402 (Payment) or 400-499 (Client error), don't retry
                if (res.status === 402 || (res.status >= 400 && res.status < 500)) {
                    const errorData = await res.json();
                    throw new Error(errorData.detail || `Server error: ${res.status}`);
                }
                // For 500s, throw to trigger retry
                const errorText = await res.text();
                throw new Error(`Server error ${res.status}: ${errorText}`);
            }
            
            const result = await res.json();
            
            // Check if schedule was extracted
            let scheduleMsg = "";
            if (result.schedule_pdf) {
                scheduleMsg = `\n\nI extracted the **Project Schedule** for ${filename} into a separate PDF.`;
            }
            
            // Add summary message
            setMessages(prev => [...prev, { 
                role: 'assistant', 
                content: `**${filename}**: Analysis Complete! ${scheduleMsg} Check the Report tab for details.` 
            }]);
            
            // Update result view only if it's the latest
            setAnalysisResult(result);
            setActiveTab('summary'); // Default to Summary tab
            return; // Success, exit loop
            
        } catch (err) {
            console.warn(`Analysis attempt ${attempt + 1} failed:`, err);
            // If it's the last attempt or a non-retriable error (handled above), rethrow
            if (attempt === retries - 1 || err.message.includes("Payment Required") || err.message.includes("Quota Exceeded")) {
                throw err;
            }
            // Wait before retry (exponential backoff)
            await new Promise(r => setTimeout(r, 1000 * Math.pow(2, attempt)));
        }
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !sessionId) return;
    
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: userMsg.content })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I encountered an error." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-[hsl(var(--neutral-100))] font-sans text-gray-900">
      
      {/* Sidebar */}
      <div className={`${isSidebarOpen ? 'w-80' : 'w-0'} bg-white border-r border-gray-200 flex flex-col transition-all duration-300 overflow-hidden`}>
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
           <div className="font-bold text-[hsl(var(--brand-navy))] flex items-center gap-2">
             <div className="w-8 h-8 bg-[hsl(var(--brand-blue))] rounded-md flex items-center justify-center text-white">ABS</div>
             Contract Admin
           </div>
        </div>
        
        <div className="p-4 flex-1 overflow-y-auto">
            <Button variant="outline" className="w-full justify-start gap-2 mb-4" onClick={createNewSession}>
                <MessageSquare size={16} /> New Chat
            </Button>
            
            {/* Live Processing Status Bar */}
            {(isProcessing || processingStatus.stage) && (
                <div className={`mb-4 p-3 rounded-lg border ${
                    processingStatus.stage === 'error' 
                        ? 'bg-red-50 border-red-200' 
                        : processingStatus.stage === 'complete'
                        ? 'bg-green-50 border-green-200'
                        : 'bg-blue-50 border-blue-200'
                }`}>
                    {/* Stage indicator with animated icon */}
                    <div className="flex items-center gap-2 mb-2">
                        {processingStatus.stage === 'uploading' && (
                            <Upload size={14} className="text-blue-600 animate-bounce" />
                        )}
                        {processingStatus.stage === 'extracting' && (
                            <FileText size={14} className="text-blue-600 animate-pulse" />
                        )}
                        {processingStatus.stage === 'analyzing' && (
                            <div className="w-3.5 h-3.5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                        )}
                        {processingStatus.stage === 'complete' && (
                            <CheckCircle size={14} className="text-green-600" />
                        )}
                        {processingStatus.stage === 'error' && (
                            <AlertTriangle size={14} className="text-red-600" />
                        )}
                        <span className={`text-xs font-semibold uppercase ${
                            processingStatus.stage === 'error' ? 'text-red-700' :
                            processingStatus.stage === 'complete' ? 'text-green-700' :
                            'text-blue-700'
                        }`}>
                            {processingStatus.stage === 'uploading' && 'Uploading'}
                            {processingStatus.stage === 'extracting' && 'Extracting Text'}
                            {processingStatus.stage === 'analyzing' && 'AI Analysis'}
                            {processingStatus.stage === 'complete' && 'Complete'}
                            {processingStatus.stage === 'error' && 'Error'}
                        </span>
                    </div>
                    
                    {/* Filename */}
                    <div className="text-xs text-gray-600 truncate mb-2">
                        {processingStatus.filename}
                    </div>
                    
                    {/* Progress bar with animated gradient */}
                    <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                        <div 
                            className={`h-2 rounded-full transition-all duration-500 ${
                                processingStatus.stage === 'error' 
                                    ? 'bg-red-500' 
                                    : processingStatus.stage === 'complete'
                                    ? 'bg-green-500'
                                    : 'bg-gradient-to-r from-blue-500 via-blue-600 to-blue-500 bg-[length:200%_100%] animate-shimmer'
                            }`}
                            style={{ width: `${processingStatus.progress}%` }}
                        ></div>
                    </div>
                    
                    {/* Status message */}
                    <div className={`text-xs mt-2 ${
                        processingStatus.stage === 'error' ? 'text-red-600' :
                        processingStatus.stage === 'complete' ? 'text-green-600' :
                        'text-blue-600'
                    }`}>
                        {processingStatus.message}
                    </div>
                    
                    {/* File count if multiple */}
                    {processingStats.total > 1 && (
                        <div className="flex justify-between text-[10px] text-gray-500 mt-2 pt-2 border-t border-gray-200">
                            <span>File {processingStats.completed + 1} of {processingStats.total}</span>
                            <span>{Math.round((processingStats.completed / processingStats.total) * 100)}% overall</span>
                        </div>
                    )}
                </div>
            )}

            {/* CONTRACT DOCUMENTS SECTION */}
            <div className="mb-4">
                <div className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider flex items-center gap-2">
                    <FileText size={12} className="text-blue-600" />
                    Contract Documents
                </div>
                <div className="space-y-2">
                    {contracts.map(doc => (
                        <div 
                            key={doc.file_id} 
                            className={`p-2 rounded border text-sm ${
                                doc.is_active 
                                    ? 'bg-blue-50 border-blue-300' 
                                    : 'bg-gray-50 border-gray-100'
                            }`}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 min-w-0 flex-1">
                                    <FileText size={14} className={doc.is_active ? 'text-blue-600' : 'text-gray-400'}/>
                                    <span className="truncate text-xs">{doc.filename}</span>
                                </div>
                                <div className="flex items-center gap-1 flex-shrink-0">
                                    {doc.is_active ? (
                                        <span className="text-[10px] bg-blue-600 text-white px-1.5 py-0.5 rounded font-semibold">ACTIVE</span>
                                    ) : (
                                        <button 
                                            onClick={() => setDocumentActive(doc.file_id, 'contract')}
                                            className="text-[10px] bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded hover:bg-gray-300"
                                        >
                                            Set Active
                                        </button>
                                    )}
                                    <button 
                                        onClick={() => deleteDocument(doc.file_id, 'contract')}
                                        className="text-gray-400 hover:text-red-500 p-0.5"
                                    >
                                        <X size={12} />
                                    </button>
                                </div>
                            </div>
                            <div className="text-[10px] text-gray-400 mt-1 flex items-center gap-1">
                                <Calendar size={10} />
                                {formatDate(doc.upload_date)}
                                {!doc.is_active && <span className="ml-1 text-gray-300">• Previous</span>}
                            </div>
                        </div>
                    ))}
                    {contracts.length === 0 && (
                        <div className="text-xs text-gray-400 italic p-2">No contracts uploaded</div>
                    )}
                </div>
            </div>

            {/* PROPOSAL DOCUMENTS SECTION */}
            <div className="mb-4">
                <div className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider flex items-center gap-2">
                    <File size={12} className="text-green-600" />
                    Proposal Documents
                </div>
                <div className="space-y-2">
                    {proposals.map(doc => (
                        <div 
                            key={doc.file_id} 
                            className={`p-2 rounded border text-sm ${
                                doc.is_active 
                                    ? 'bg-green-50 border-green-300' 
                                    : 'bg-gray-50 border-gray-100'
                            }`}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 min-w-0 flex-1">
                                    <File size={14} className={doc.is_active ? 'text-green-600' : 'text-gray-400'}/>
                                    <span className="truncate text-xs">{doc.filename}</span>
                                </div>
                                <div className="flex items-center gap-1 flex-shrink-0">
                                    {doc.is_active ? (
                                        <span className="text-[10px] bg-green-600 text-white px-1.5 py-0.5 rounded font-semibold">ACTIVE</span>
                                    ) : (
                                        <button 
                                            onClick={() => setDocumentActive(doc.file_id, 'proposal')}
                                            className="text-[10px] bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded hover:bg-gray-300"
                                        >
                                            Set Active
                                        </button>
                                    )}
                                    <button 
                                        onClick={() => deleteDocument(doc.file_id, 'proposal')}
                                        className="text-gray-400 hover:text-red-500 p-0.5"
                                    >
                                        <X size={12} />
                                    </button>
                                </div>
                            </div>
                            <div className="text-[10px] text-gray-400 mt-1 flex items-center gap-1">
                                <Calendar size={10} />
                                {formatDate(doc.upload_date)}
                                {!doc.is_active && <span className="ml-1 text-gray-300">• Previous</span>}
                            </div>
                        </div>
                    ))}
                    {proposals.length === 0 && (
                        <div className="text-xs text-gray-400 italic p-2">No proposals uploaded</div>
                    )}
                </div>
            </div>

            <div className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">Task Type</div>
            <select 
                className="w-full p-2 text-sm border rounded mb-4" 
                value={taskType} 
                onChange={(e) => setTaskType(e.target.value)}
            >
                <option value="INITIAL_CONTRACT_REVIEW">Initial Contract Review</option>
                <option value="SCOPE_REVIEW">Scope Review (Proposal vs Contract)</option>
                <option value="SCHEDULE_ANALYSIS">Schedule Extraction & Analysis</option>
                <option value="PROPOSAL_COMPARISON_AND_EXHIBIT">Proposal Comparison</option>
                <option value="PM_CONTRACT_REVIEW_SUMMARY">PM Review Summary</option>
                <option value="PROCORE_MAPPING">Procore Mapping</option>
                <option value="ACCOUNT_MANAGER_SUMMARY_EMAIL">Account Manager Email</option>
                <option value="NEGOTIATION_SUGGESTED_REPLY">Negotiation Reply</option>
                <option value="POST_EXECUTION_SUMMARY">Post-Execution Summary</option>
            </select>
        </div>

        {/* Upload Zones at bottom of sidebar */}
        <div className="p-4 border-t border-gray-200 bg-gray-50 space-y-3">
            {/* Contract Upload */}
            <label className="flex flex-col items-center justify-center w-full h-16 border-2 border-dashed border-blue-300 rounded-lg cursor-pointer hover:bg-blue-50 transition-colors bg-white">
                <div className="flex flex-col items-center justify-center">
                    <Upload className="w-5 h-5 text-blue-500 mb-1" />
                    <p className="text-xs text-blue-600 font-medium">Upload Contract</p>
                </div>
                <input type="file" className="hidden" onChange={handleContractUpload} accept=".pdf,.docx" multiple />
            </label>
            
            {/* Proposal Upload */}
            <label className="flex flex-col items-center justify-center w-full h-16 border-2 border-dashed border-green-300 rounded-lg cursor-pointer hover:bg-green-50 transition-colors bg-white">
                <div className="flex flex-col items-center justify-center">
                    <Upload className="w-5 h-5 text-green-500 mb-1" />
                    <p className="text-xs text-green-600 font-medium">Click to upload Proposal</p>
                </div>
                <input type="file" className="hidden" onChange={handleProposalUpload} accept=".pdf,.docx" multiple />
            </label>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 p-4 flex items-center justify-between shadow-sm z-10">
            <div className="flex items-center gap-3">
                <button onClick={() => setSidebarOpen(!isSidebarOpen)} className="p-2 hover:bg-gray-100 rounded-md">
                    <Menu size={20} />
                </button>
                <h1 className="font-semibold text-lg truncate">
                    {taskType.replace(/_/g, " ")}
                </h1>
            </div>
            <div className="flex items-center gap-2">
                <Tabs 
                    activeTab={activeTab} 
                    setActiveTab={setActiveTab} 
                    tabs={[
                        {id: 'chat', label: 'Chat'}, 
                        {id: 'summary', label: 'Summary'},
                        {id: 'terms', label: 'Terms'},
                        {id: 'scope', label: 'Scope'},
                        {id: 'history', label: 'History'},
                        {id: 'json', label: 'Raw Data'}
                    ]} 
                />
            </div>
        </header>

        {/* Floating Processing Status Bar */}
        {(isProcessing || (processingStatus.stage && processingStatus.stage !== '')) && (
            <div className={`mx-4 mt-2 p-3 rounded-lg shadow-lg border transition-all duration-300 ${
                processingStatus.stage === 'error' 
                    ? 'bg-red-50 border-red-300' 
                    : processingStatus.stage === 'complete'
                    ? 'bg-green-50 border-green-300'
                    : 'bg-white border-blue-300'
            }`}>
                <div className="flex items-center justify-between gap-4">
                    {/* Left side - Status info */}
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                        {/* Animated icon */}
                        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                            processingStatus.stage === 'error' ? 'bg-red-100' :
                            processingStatus.stage === 'complete' ? 'bg-green-100' :
                            'bg-blue-100 animate-pulse-glow'
                        }`}>
                            {processingStatus.stage === 'uploading' && (
                                <Upload size={16} className="text-blue-600 animate-bounce" />
                            )}
                            {processingStatus.stage === 'extracting' && (
                                <FileText size={16} className="text-blue-600 animate-pulse" />
                            )}
                            {processingStatus.stage === 'analyzing' && (
                                <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                            )}
                            {processingStatus.stage === 'complete' && (
                                <CheckCircle size={16} className="text-green-600" />
                            )}
                            {processingStatus.stage === 'error' && (
                                <AlertTriangle size={16} className="text-red-600" />
                            )}
                        </div>
                        
                        {/* Status text */}
                        <div className="min-w-0 flex-1">
                            <div className={`text-sm font-semibold ${
                                processingStatus.stage === 'error' ? 'text-red-700' :
                                processingStatus.stage === 'complete' ? 'text-green-700' :
                                'text-blue-700'
                            }`}>
                                {processingStatus.message}
                            </div>
                            <div className="text-xs text-gray-500 truncate">
                                {processingStatus.filename}
                            </div>
                        </div>
                    </div>
                    
                    {/* Right side - Progress */}
                    <div className="flex items-center gap-3 flex-shrink-0">
                        {processingStats.total > 1 && (
                            <span className="text-xs text-gray-500">
                                {processingStats.completed + 1}/{processingStats.total}
                            </span>
                        )}
                        <div className="w-24 bg-gray-200 rounded-full h-2 overflow-hidden">
                            <div 
                                className={`h-2 rounded-full transition-all duration-300 ${
                                    processingStatus.stage === 'error' 
                                        ? 'bg-red-500' 
                                        : processingStatus.stage === 'complete'
                                        ? 'bg-green-500'
                                        : 'bg-gradient-to-r from-blue-500 via-blue-400 to-blue-500 bg-[length:200%_100%] animate-shimmer'
                                }`}
                                style={{ width: `${processingStatus.progress}%` }}
                            ></div>
                        </div>
                        <span className={`text-sm font-bold min-w-[40px] text-right ${
                            processingStatus.stage === 'error' ? 'text-red-600' :
                            processingStatus.stage === 'complete' ? 'text-green-600' :
                            'text-blue-600'
                        }`}>
                            {processingStatus.progress}%
                        </span>
                    </div>
                </div>
            </div>
        )}

        {/* Workspace */}
        <div className="flex-1 overflow-hidden relative">
            
            {/* Chat View */}
            <div className={`absolute inset-0 flex flex-col bg-white transition-opacity duration-200 ${activeTab === 'chat' ? 'opacity-100 z-10' : 'opacity-0 -z-10 pointer-events-none'}`}>
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-3xl rounded-lg p-4 shadow-sm ${
                                msg.role === 'user' 
                                    ? 'bg-[hsl(var(--brand-blue))] text-white' 
                                    : 'bg-white border border-gray-200 text-gray-800'
                            }`}>
                                <div className="prose prose-sm max-w-none">
                                    {msg.role === 'system' ? (
                                        <div className="flex items-center gap-2 italic text-gray-500">
                                            <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {msg.content}
                                            </ReactMarkdown>
                                        </div>
                                    ) : (
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {msg.content}
                                        </ReactMarkdown>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>
                <div className="p-4 bg-white border-t border-gray-200">
                    <div className="flex gap-2 max-w-4xl mx-auto">
                        <input 
                            className="flex-1 border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="Ask about the contract..."
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && sendMessage()}
                            disabled={isLoading}
                        />
                        <Button onClick={sendMessage} disabled={isLoading}>
                            {isLoading ? '...' : <Play size={16} fill="currentColor" />}
                        </Button>
                    </div>
                </div>
            </div>

            {/* Summary Tab (New) */}
            <div className={`absolute inset-0 overflow-y-auto p-8 bg-white transition-opacity duration-200 ${activeTab === 'summary' ? 'opacity-100 z-10' : 'opacity-0 -z-10 pointer-events-none'}`}>
                {analysisResult?.structured_data?.summary_data ? (
                    <div className="max-w-4xl mx-auto">
                        <SummaryView data={analysisResult.structured_data.summary_data} />
                    </div>
                ) : (
                    <div className="flex h-full items-center justify-center text-gray-400">
                        No summary available. Run an Initial Contract Review first.
                    </div>
                )}
            </div>

            {/* Negotiations Tab (Terms) */}
            <div className={`absolute inset-0 overflow-y-auto p-8 bg-white transition-opacity duration-200 ${activeTab === 'terms' ? 'opacity-100 z-10' : 'opacity-0 -z-10 pointer-events-none'}`}>
                {analysisResult?.structured_data?.negotiation_summary ? (
                    <div className="max-w-4xl mx-auto">
                        <NegotiationView data={analysisResult.structured_data.negotiation_summary} />
                    </div>
                ) : (
                    <div className="flex h-full items-center justify-center text-gray-400">
                        No negotiation items found. Run an Initial Contract Review first.
                    </div>
                )}
            </div>

            {/* Scope Tab */}
            <div className={`absolute inset-0 overflow-y-auto p-8 bg-white transition-opacity duration-200 ${activeTab === 'scope' ? 'opacity-100 z-10' : 'opacity-0 -z-10 pointer-events-none'}`}>
                {analysisResult?.structured_data?.scope_data ? (
                    <div className="max-w-4xl mx-auto">
                        <ScopeView data={analysisResult.structured_data.scope_data} />
                    </div>
                ) : (
                    <div className="flex flex-col h-full items-center justify-center text-gray-400">
                        <div className="text-center max-w-md">
                            <div className="text-lg font-semibold mb-2">Scope Review</div>
                            <p className="text-sm mb-4">
                                Upload a Proposal document to begin scope review.
                                The Proposal defines what ABS priced and serves as the authoritative baseline.
                            </p>
                            <p className="text-xs text-gray-300">
                                When both Proposal and Contract are uploaded, the system will compare each scope for alignment.
                            </p>
                        </div>
                    </div>
                )}
            </div>

            {/* History Tab */}
            <div className={`absolute inset-0 overflow-y-auto p-8 bg-white transition-opacity duration-200 ${activeTab === 'history' ? 'opacity-100 z-10' : 'opacity-0 -z-10 pointer-events-none'}`}>
                <div className="max-w-4xl mx-auto">
                    <HistoryView 
                        reviews={reviewHistory}
                        onLoadReview={loadReviewFromHistory}
                        onDeleteReview={deleteReviewFromHistory}
                        onRefresh={loadHistory}
                        isLoading={isHistoryLoading}
                    />
                </div>
            </div>

            {/* JSON View */}
             <div className={`absolute inset-0 overflow-y-auto p-4 bg-gray-50 transition-opacity duration-200 ${activeTab === 'json' ? 'opacity-100 z-10' : 'opacity-0 -z-10 pointer-events-none'}`}>
                {analysisResult ? (
                     <JsonView data={analysisResult} shouldExpandNode={() => true} style={defaultStyles} />
                ) : (
                    <div className="flex h-full items-center justify-center text-gray-400">
                        No data available.
                    </div>
                )}
            </div>

        </div>
      </div>
    </div>
  );
}
