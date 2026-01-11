'use client';

import React, { useEffect, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    faArrowLeft,
    faSpinner,
    faDownload,
    faPaperPlane,
    faPlus,
    faHistory,
    faBolt,
    faGear,
    faTrash,
    faFileAlt,
    faMessage,
    faTerminal,
    faChevronUp,
    faChevronDown
} from "@fortawesome/free-solid-svg-icons";
import { Instrument_Sans } from "next/font/google";
import { Panel, Group, Separator } from 'react-resizable-panels';
import { getJob, getFileUrl, Job, getJobEvents, AgentEvent, queryJobMemory, deleteJob } from '../../../../services/jobs';
import { useJobEvents, ConnectionStatus, ConnectionError } from '../../../../hooks/useJobEvents';
import StepViewer from '../../../../components/StepViewer';
import {C1Component} from "@thesysai/genui-sdk";

const instrument_sans = Instrument_Sans({
    weight: ["400", "500", "600"],
    subsets: ["latin"],
});

export default function JobPage() {
    const params = useParams();
    const router = useRouter();
    const id = params?.id as string;
    const [job, setJob] = useState<Job | null>(null);
    const [loading, setLoading] = useState(true);
    const [initialEventsLoaded, setInitialEventsLoaded] = useState(false);
    const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
    const [loadingAnalysis, setLoadingAnalysis] = useState(false);

    // Chat state
    const [messages, setMessages] = useState<{ role: 'user' | 'ai', content: string }[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // View state
    const [initialEvents, setInitialEvents] = useState<AgentEvent[]>([]);
    const bottomPanelRef = useRef<any>(null);
    const [bottomPanelCollapsed, setBottomPanelCollapsed] = useState(false);

    // Settings state
    const [showSettings, setShowSettings] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const settingsRef = useRef<HTMLDivElement>(null);

    // Use WebSocket for real-time event streaming
    // Only pass initialEvents once they've been loaded to avoid race condition
    const { events, isConnected, connectionStatus, connectionError } = useJobEvents(
        initialEventsLoaded ? id : null,
        initialEvents
    );

    useEffect(() => {
        if (id) {
            // Load job and initial events in parallel, wait for both
            Promise.all([
                getJob(id),
                getJobEvents(id)
            ]).then(([jobData, eventsData]) => {
                setJob(jobData);
                setInitialEvents(eventsData);
                setInitialEventsLoaded(true);
                setLoading(false);

                // Fetch analysis results if job is completed
                if (jobData && (jobData.status === 'COMPLETED' || jobData.status === 'completed')) {
                    setLoadingAnalysis(true);
                    getJobAnalysisResults(id).then((result) => {
                        setAnalysisResult(result);
                        setLoadingAnalysis(false);
                    }).catch(() => {
                        setLoadingAnalysis(false);
                    });
                }
            }).catch((error) => {
                console.error('Failed to load job data:', error);
                setLoading(false);
            });
        }
    }, [id]);

    // Close settings dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (settingsRef.current && !settingsRef.current.contains(event.target as Node)) {
                setShowSettings(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleDeleteClick = () => {
        setShowDeleteConfirm(true);
        setShowSettings(false);
    };

    const handleConfirmDelete = async () => {
        setIsDeleting(true);
        const success = await deleteJob(id);
        if (success) {
            router.push('/');
        } else {
            setIsDeleting(false);
            setShowDeleteConfirm(false);
        }
    };

    const handleSendMessage = async () => {
        if (!inputValue.trim() || isLoading) return;

        const userMessage = inputValue.trim();
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setInputValue('');
        setIsLoading(true);

        try {
            const response = await queryJobMemory(id, userMessage);
            if (response) {
                setMessages(prev => [...prev, {
                    role: 'ai',
                    content: response.answer + (response.sourcesUsed > 0 ? `\n\n📚 Based on ${response.sourcesUsed} source${response.sourcesUsed > 1 ? 's' : ''} from the analysis.` : '')
                }]);
            } else {
                setMessages(prev => [...prev, {
                    role: 'ai',
                    content: "Sorry, I couldn't process your question. Please try again."
                }]);
            }
        } catch (error) {
            console.error("Chat error:", error);
            setMessages(prev => [...prev, {
                role: 'ai',
                content: "An error occurred while processing your question."
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="w-full h-full flex flex-col items-center justify-center bg-zinc-50 gap-4">
                <div className="relative w-12 h-12">
                    <div className="absolute inset-0 border-4 border-zinc-200 rounded-full"></div>
                    <div className="absolute inset-0 border-4 border-t-primary border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin"></div>
                </div>
            </div>
        );
    }

    if (!job) {
        return (
            <div className="flex flex-col items-center justify-center w-full h-full gap-4 p-12 bg-zinc-50">
                <p className="text-zinc-500">Job not found.</p>
                <Link href="/" className="text-primary hover:underline">Go back home</Link>
            </div>
        );
    }

    return (
        <div className="flex flex-col w-full h-full overflow-hidden bg-zinc-50">
            {/* Delete Confirmation Modal */}
            {showDeleteConfirm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white border border-zinc-200 shadow-xl p-6 max-w-sm w-full mx-4">
                        <h3 className={`text-lg font-semibold text-zinc-900 mb-2 ${instrument_sans.className}`}>Delete Job?</h3>
                        <p className="text-sm text-zinc-500 mb-6">This action cannot be undone. The job and all associated data will be permanently deleted.</p>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setShowDeleteConfirm(false)}
                                disabled={isDeleting}
                                className="px-4 py-2 text-sm font-medium text-zinc-600 bg-zinc-100 border border-zinc-200 hover:bg-zinc-200 transition-colors cursor-pointer disabled:opacity-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleConfirmDelete}
                                disabled={isDeleting}
                                className="px-4 py-2 text-sm font-medium text-white bg-red-500 border border-red-500 hover:bg-red-600 transition-colors cursor-pointer flex items-center gap-2 disabled:opacity-50"
                            >
                                {isDeleting ? (
                                    <>
                                        <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                                        Deleting...
                                    </>
                                ) : (
                                    <>
                                        <FontAwesomeIcon icon={faTrash} />
                                        Delete
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Top Bar / Data Nav */}
            <div className={`h-13.5 border-b border-zinc-200 bg-white flex items-center justify-between px-6 shrink-0 z-20 ${instrument_sans.className}`}>
                <div className="flex items-center gap-4 overflow-hidden">
                    <Link href="/" className="flex items-center justify-center w-8 h-8 hover:bg-zinc-100 text-zinc-500 transition-colors">
                        <FontAwesomeIcon icon={faArrowLeft} className="text-sm" />
                    </Link>

                    <div className="h-6 w-px bg-zinc-200 mx-2 hidden md:block"></div>

                    <div className="flex flex-col">
                        <h1 className="text-sm font-semibold text-zinc-900 truncate max-w-[200px]">{job.originalFilename}</h1>
                        <span className="text-[10px] text-zinc-500 font-mono">{job.id}</span>
                    </div>

                    <div className="hidden md:flex items-center gap-4 ml-6">
                        <div className="flex flex-col">
                            <span className="text-[10px] uppercase text-zinc-400 font-bold tracking-wider">Status</span>
                            <span className="text-xs font-medium text-zinc-700 capitalize">{job.status.replace('_', ' ')}</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="text-[10px] uppercase text-zinc-400 font-bold tracking-wider">Process</span>
                            <span className="text-xs font-medium text-zinc-700">{job.manufacturingProcess}</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="text-[10px] uppercase text-zinc-400 font-bold tracking-wider">Material</span>
                            <span className="text-xs font-medium text-zinc-700">PLA</span>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <a
                        href={getFileUrl(job.fileStorageId)}
                        className="bg-zinc-100 text-zinc-700 px-3 py-1.5 text-xs font-medium hover:bg-zinc-200 transition-colors flex items-center gap-2 border border-zinc-200"
                        download
                    >
                        <FontAwesomeIcon icon={faDownload} />
                        Download
                    </a>

                    {/* Settings Dropdown */}
                    <div className="relative" ref={settingsRef}>
                        <button
                            onClick={() => setShowSettings(!showSettings)}
                            className="w-8 h-8 flex items-center justify-center text-zinc-500 hover:text-zinc-800 hover:bg-zinc-100 border border-zinc-200 transition-colors cursor-pointer"
                            title="Settings"
                        >
                            <FontAwesomeIcon icon={faGear} className="text-sm" />
                        </button>

                        {showSettings && (
                            <div className="absolute right-0 top-full mt-1 bg-white border border-zinc-200 shadow-lg z-50 min-w-[160px]">
                                <button
                                    onClick={handleDeleteClick}
                                    className="w-full px-4 py-2.5 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-3 transition-colors cursor-pointer"
                                >
                                    <FontAwesomeIcon icon={faTrash} className="text-xs" />
                                    Delete Job
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col overflow-hidden">
                <Group orientation="vertical" className="flex-1">
                    {/* Top Half: Resizable Render + Markdown */}
                    <Panel defaultSize={50} minSize={20} className="flex overflow-hidden">
                        <Group orientation="horizontal" className="flex-1">
                            {/* Left: 3D Render */}
                            <Panel defaultSize={50} minSize={20} className="bg-zinc-900 relative">
                                {job.fileStorageId ? (
                                    <StepViewer url={getFileUrl(job.fileStorageId)} />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center text-zinc-500">
                                        No Model Data
                                    </div>
                                )}
                            </Panel>

                            <Separator className="w-1 bg-zinc-200 hover:bg-zinc-300 transition-colors cursor-col-resize" />

                            {/* Right: Markdown Documentation */}
                            <Panel defaultSize={50} minSize={20} className="bg-white flex flex-col">
                                <div className="h-10 border-b border-zinc-100 flex items-center justify-between px-4 bg-zinc-50 shrink-0">
                                    <div className="flex items-center gap-2">
                                        <FontAwesomeIcon icon={faFileAlt} className="text-zinc-400 text-xs" />
                                        <span className="text-[11px] font-semibold text-zinc-600 uppercase tracking-wider">Analysis Report</span>
                                    </div>
                                    <span className="text-[10px] text-zinc-400 font-mono">analysis.md</span>
                                </div>
                                <div className="flex-1 overflow-y-auto p-8">
                                    <div className="prose prose-sm prose-zinc max-w-none 
                                        prose-headings:text-zinc-900 prose-headings:font-bold
                                        prose-h1:text-xl prose-h1:mb-6 prose-h1:pb-2 prose-h1:border-b prose-h1:border-zinc-100
                                        prose-h2:text-sm prose-h2:uppercase prose-h2:tracking-wider prose-h2:text-zinc-500 prose-h2:mt-8 prose-h2:mb-4
                                        prose-p:text-zinc-600 prose-p:leading-relaxed
                                        prose-table:border prose-table:border-zinc-100 prose-table:rounded-lg prose-table:overflow-hidden
                                        prose-thead:bg-zinc-50 prose-th:px-4 prose-th:py-2 prose-th:text-zinc-700
                                        prose-td:px-4 prose-td:py-2 prose-td:border-t prose-td:border-zinc-50
                                        prose-code:bg-zinc-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-zinc-800
                                        prose-pre:bg-zinc-900 prose-pre:text-zinc-100 prose-pre:p-4 prose-pre:rounded-none
                                    ">
                                        <ReactMarkdown>{placeholderMarkdown}</ReactMarkdown>
                                    </div>
                                </div>
                            </Panel>
                        </Group>
                    </Panel>

                    <Separator className="h-1 bg-zinc-200 hover:bg-zinc-300 transition-colors cursor-row-resize relative group">
                        <button
                            onClick={() => {
                                if (bottomPanelRef.current) {
                                    if (bottomPanelCollapsed) {
                                        bottomPanelRef.current.expand();
                                    } else {
                                        bottomPanelRef.current.collapse();
                                    }
                                }
                                setBottomPanelCollapsed(!bottomPanelCollapsed);
                            }}
                            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center bg-white border border-zinc-300 shadow-sm hover:bg-zinc-50 transition-colors cursor-pointer z-20 pointer-events-auto"
                            title={bottomPanelCollapsed ? "Expand bottom panel" : "Collapse bottom panel"}
                            onMouseEnter={(e) => {
                                e.stopPropagation();
                            }}
                            onMouseDown={(e) => {
                                e.stopPropagation();
                            }}
                        >
                            <FontAwesomeIcon 
                                icon={bottomPanelCollapsed ? faChevronUp : faChevronDown} 
                                className="text-xs text-zinc-600" 
                            />
                        </button>
                    </Separator>

                    {/* Bottom Half: AI Chat + Live Events (Side by Side) */}
                    <Panel 
                        panelRef={bottomPanelRef}
                        defaultSize={50} 
                        minSize={260}
                        collapsible={true}
                        collapsedSize={50}
                        className="flex flex-col bg-white border-t border-zinc-200"
                    >
                        <Group orientation="horizontal" className="flex-1">
                            {/* Left: AI Assistant Chat */}
                            <Panel defaultSize={50} minSize={20} className="flex flex-col bg-white">
                                {/* AI Assistant Header */}
                                <div className="h-11 border-b border-zinc-200 flex items-center justify-between px-6 bg-white shrink-0">
                                    <div className="flex items-center gap-2">
                                        <FontAwesomeIcon icon={faMessage} className="text-[10px] text-zinc-400" />
                                        <span className="text-xs font-semibold text-zinc-900">AI Assistant</span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <button className="p-2 text-zinc-400 hover:text-zinc-900 transition-colors cursor-pointer" title="Chat History">
                                            <FontAwesomeIcon icon={faHistory} className="text-xs" />
                                        </button>
                                        <button
                                            onClick={() => setMessages([])}
                                            className="p-2 text-zinc-400 hover:text-zinc-900 transition-colors cursor-pointer"
                                            title="New Discussion"
                                        >
                                            <FontAwesomeIcon icon={faPlus} className="text-xs" />
                                        </button>
                                    </div>
                                </div>

                                {/* Chat Content */}
                                <div className="flex-1 flex flex-col overflow-hidden bg-zinc-50/20">
                                    <div className="flex-1 flex flex-col w-full px-6 overflow-hidden">
                                        <div className="flex-1 overflow-y-auto flex flex-col">
                                            {messages.length > 0 ? (
                                                <div className="py-4 flex flex-col gap-3">
                                                    {messages.map((msg, idx) => (
                                                        <div key={idx} className="flex justify-start">
                                                            <div className={`max-w-[75%] ${msg.role === 'user'
                                                                ? 'bg-zinc-900 text-white rounded-lg p-3'
                                                                : 'text-zinc-800'
                                                                }`}>
                                                                {msg.role === 'user' && (
                                                                    <div className="text-[9px] font-bold uppercase tracking-widest mb-1 opacity-50">
                                                                        You
                                                                    </div>
                                                                )}
                                                                {msg.role === 'ai' ? (
                                                                    <div className="text-xs leading-relaxed prose prose-sm prose-zinc max-w-none prose-invert-0 prose-p:my-1 prose-headings:my-2">
                                                                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                                                                    </div>
                                                                ) : (
                                                                    <div className="text-xs leading-relaxed whitespace-pre-wrap">
                                                                        {msg.content}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </div>
                                                    ))}
                                                    {isLoading && (
                                                        <div className="flex justify-start">
                                                            <div className="bg-white border border-zinc-200 rounded-lg p-3 flex items-center gap-2">
                                                                <FontAwesomeIcon icon={faSpinner} className="animate-spin text-primary text-xs" />
                                                                <span className="text-[10px] text-zinc-500 font-medium">Processing...</span>
                                                            </div>
                                                        </div>
                                                    )}
                                                    <div className="h-2 shrink-0"></div>
                                                </div>
                                            ) : (
                                                <div className="flex flex-col justify-center h-full w-1/2 opacity-0 animate-[fadeIn_0.5s_ease-in-out_0.2s_forwards]">
                                                    <span className="mb-3 text-zinc-500 text-sm">Get started with a prompt</span>
                                                    <div className="flex flex-col gap-2">
                                                        <button
                                                            onClick={() => {
                                                                setInputValue("What are the key manufacturing considerations for this model?");
                                                                (document.querySelector('input[type="text"]') as HTMLInputElement)?.focus();
                                                            }}
                                                            className="text-left px-4 py-1 text-xs text-zinc-700 bg-white border border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300 transition-all cursor-pointer"
                                                        >
                                                            What are the key manufacturing considerations for this model?
                                                        </button>
                                                        <button
                                                            onClick={() => {
                                                                setInputValue("What material would work best for this part?");
                                                                (document.querySelector('input[type="text"]') as HTMLInputElement)?.focus();
                                                            }}
                                                            className="text-left px-4 py-1 text-xs text-zinc-700 bg-white border border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300 transition-all cursor-pointer"
                                                        >
                                                            What material would work best for this part?
                                                        </button>
                                                        <button
                                                            onClick={() => {
                                                                setInputValue("Are there any design issues I should be aware of?");
                                                                (document.querySelector('input[type="text"]') as HTMLInputElement)?.focus();
                                                            }}
                                                            className="text-left px-4 py-1 text-xs text-zinc-700 bg-white border border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300 transition-all cursor-pointer"
                                                        >
                                                            Are there any design issues I should be aware of?
                                                        </button>
                                                    </div>
                                                </div>
                                            )}
                                        </div>

                                        <div className="py-3 bg-transparent border-t border-zinc-200 shrink-0">
                                            <div className="relative group">
                                                <div className="relative flex items-center border border-zinc-200 bg-white focus-within:border-zinc-400 transition-all duration-200 rounded">
                                                    <input
                                                        type="text"
                                                        className="w-full bg-transparent text-xs p-3 pr-10 focus:outline-none placeholder:text-zinc-400"
                                                        placeholder={isLoading ? "AI is thinking..." : "Ask a technical follow-up..."}
                                                        value={inputValue}
                                                        onChange={(e) => setInputValue(e.target.value)}
                                                        onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                                                        disabled={isLoading}
                                                    />
                                                    <button
                                                        onClick={handleSendMessage}
                                                        disabled={isLoading}
                                                        className={`absolute right-2 h-7 w-7 transition-all flex items-center justify-center rounded ${isLoading
                                                            ? 'text-zinc-300'
                                                            : 'text-zinc-100 bg-zinc-900 hover:bg-black cursor-pointer'
                                                            }`}
                                                    >
                                                        <FontAwesomeIcon icon={faPaperPlane} className="text-[9px]" />
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </Panel>

                            <Separator className="w-1 bg-zinc-200 hover:bg-zinc-300 transition-colors cursor-col-resize" />

                            {/* Right: Live Agent Feed */}
                            <Panel defaultSize={50} minSize={20} className="flex flex-col bg-white">
                                {/* Live Agent Feed Header */}
                                <div className="h-11 border-b border-zinc-200 flex items-center justify-between px-6 bg-white shrink-0">
                                    <div className="flex items-center gap-2">
                                        <FontAwesomeIcon icon={faTerminal} className="text-[10px] text-zinc-400" />
                                        <span className="text-xs font-semibold text-primary">Live Agent Feed</span>
                                        <span className={`flex items-center gap-1.5 ml-2 px-1.5 py-0.5 bg-zinc-100 rounded text-[9px] ${isConnected ? 'text-green-600' : 'text-zinc-400'}`}>
                                            <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-zinc-300'}`}></span>
                                            {isConnected ? 'LIVE' : 'OFFLINE'}
                                        </span>
                                    </div>
                                </div>

                                {/* Feed Content - Horizontal Scrollable Panels */}
                                <div className="flex-1 overflow-hidden bg-white">
                                    {events.length === 0 ? (
                                        <div className="flex flex-col items-center justify-center h-full py-12 text-zinc-300">
                                            <FontAwesomeIcon icon={faBolt} className="text-2xl mb-3 opacity-20" />
                                            <span className="text-[9px] font-bold tracking-[0.2em] uppercase">No events logged</span>
                                        </div>
                                    ) : (
                                        <Group orientation="horizontal" className="h-full">
                                            {events.map((event, index) => (
                                                <React.Fragment key={event.id}>
                                                    <Panel defaultSize={events.length > 0 ? 100 / events.length : 100} minSize={15} className="flex flex-col border-r border-zinc-200 overflow-hidden">
                                                        <div className="h-8 border-b border-zinc-100 flex items-center justify-between px-3 bg-zinc-50 shrink-0">
                                                            <div className="flex items-center gap-2">
                                                                <div className={`w-1.5 h-1.5 rounded-full ${event.type === 'ERROR' ? 'bg-red-500' :
                                                                    event.type === 'SUCCESS' ? 'bg-green-500' :
                                                                        event.type === 'THINKING' ? 'bg-yellow-400 animate-pulse' :
                                                                            'bg-blue-500'
                                                                    }`}></div>
                                                                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${event.type === 'ERROR' ? 'bg-red-50 text-red-500' :
                                                                    event.type === 'SUCCESS' ? 'bg-green-50 text-green-600' :
                                                                        event.type === 'THINKING' ? 'bg-yellow-50 text-yellow-600' :
                                                                            'bg-blue-50 text-blue-600'
                                                                    }`}>
                                                                    {event.type}
                                                                </span>
                                                                <span className="text-[10px] font-bold text-zinc-700 truncate">{event.title}</span>
                                                            </div>
                                                            <span className="text-[9px] text-zinc-400 font-mono shrink-0">
                                                                {new Date(event.createdAt).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                                            </span>
                                                        </div>
                                                        <div className="flex-1 overflow-y-auto px-3 py-2 font-mono">
                                                            {event.content ? (
                                                                <p className="text-[10px] text-zinc-600 whitespace-pre-wrap leading-relaxed">
                                                                    {event.content}
                                                                </p>
                                                            ) : (
                                                                <p className="text-[10px] text-zinc-400 italic">No content</p>
                                                            )}
                                                        </div>
                                                    </Panel>
                                                    {index < events.length - 1 && (
                                                        <Separator className="w-1 bg-zinc-200 hover:bg-zinc-300 transition-colors cursor-col-resize" />
                                                    )}
                                                </React.Fragment>
                                            ))}
                                        </Group>
                                    )}
                                </div>
                            </Panel>
                        </Group>
                    </Panel>
                </Group>
            </div>
        </div>
    );
}
