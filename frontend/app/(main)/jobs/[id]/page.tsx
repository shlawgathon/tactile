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
    faTrash
} from "@fortawesome/free-solid-svg-icons";
import { Instrument_Sans } from "next/font/google";
import { getJob, getFileUrl, Job, getJobEvents, AgentEvent, queryJobMemory, deleteJob } from '../../../../services/jobs';
import { useJobEvents } from '../../../../hooks/useJobEvents';
import StepViewer from '../../../../components/StepViewer';

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

    // Chat state
    const [messages, setMessages] = useState<{ role: 'user' | 'ai', content: string }[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // View state
    const [activeTab, setActiveTab] = useState<'chat' | 'feed'>('chat');
    const [initialEvents, setInitialEvents] = useState<AgentEvent[]>([]);

    // Settings state
    const [showSettings, setShowSettings] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const settingsRef = useRef<HTMLDivElement>(null);

    // Use WebSocket for real-time event streaming
    const { events, isConnected, connectionError } = useJobEvents(id, initialEvents);

    useEffect(() => {
        if (id) {
            getJob(id).then(data => {
                setJob(data);
                setLoading(false);
            });
            // Initial fetch of events via REST API
            getJobEvents(id).then(setInitialEvents);
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
        <div className="flex flex-col w-full h-full overflow-hidden">
            {/* Delete Confirmation Modal */}
            {showDeleteConfirm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white border border-gray-200 shadow-xl p-6 max-w-sm w-full mx-4">
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
            <div className={`h-13.5 border-b border-gray-200 bg-white flex items-center justify-between px-6 shrink-0 z-20 ${instrument_sans.className}`}>
                <div className="flex items-center gap-4 overflow-hidden">
                    <Link href="/" className="flex items-center justify-center w-8 h-8 hover:bg-zinc-100 text-zinc-500 transition-colors">
                        <FontAwesomeIcon icon={faArrowLeft} className="text-sm" />
                    </Link>

                    <div className="h-6 w-px bg-gray-200 mx-2 hidden md:block"></div>

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
                            <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 shadow-lg z-50 min-w-[160px]">
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

            {/* Main Content: Split View */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left: 3D Viewer */}
                <div className="flex-1 bg-zinc-900 relative min-w-0">
                    {job.fileStorageId ? (
                        <StepViewer url={getFileUrl(job.fileStorageId)} />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center text-zinc-500">
                            No Model Data
                        </div>
                    )}
                </div>

                {/* Right: AI Chat / Agent Feed */}
                <div className="w-[400px] bg-white border-l border-gray-200 flex flex-col shrink-0 relative z-10 shadow-xl">

                    {/* Header with Cleaner Tabs */}
                    <div className="h-12 border-b border-gray-100 flex items-center justify-between px-2 bg-white shrink-0">
                        <div className="flex items-center gap-1 h-full">
                            <button
                                onClick={() => setActiveTab('chat')}
                                className={`cursor-pointer h-full px-4 flex items-center gap-2 text-xs font-medium border-b-2 transition-all ${activeTab === 'chat'
                                    ? 'border-zinc-800 text-zinc-900'
                                    : 'border-transparent text-zinc-400 hover:text-zinc-600'
                                    }`}
                            >
                                Chat
                            </button>
                            <button
                                onClick={() => setActiveTab('feed')}
                                className={`cursor-pointer h-full px-4 flex items-center gap-2 text-xs font-medium border-b-2 transition-all ${activeTab === 'feed'
                                    ? 'border-primary text-primary'
                                    : 'border-transparent text-zinc-400 hover:text-zinc-600'
                                    }`}
                            >
                                Agent Feed
                                {activeTab === 'feed' && (
                                    <span className={`flex items-center gap-1 text-[10px] ${isConnected ? 'text-green-500' : connectionError ? 'text-red-400' : 'text-yellow-500'}`}>
                                        <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : connectionError ? 'bg-red-400' : 'bg-yellow-500 animate-pulse'}`}></span>
                                        {isConnected ? 'Live' : connectionError ? 'Error' : 'Connecting'}
                                    </span>
                                )}
                            </button>
                        </div>

                        {activeTab === 'chat' && (
                            <div className="flex items-center gap-1 pr-2">
                                <button
                                    className="w-7 h-7 flex items-center justify-center text-zinc-400 hover:text-zinc-800 hover:bg-zinc-50 transition-all"
                                    title="History"
                                >
                                    <FontAwesomeIcon icon={faHistory} className="text-xs" />
                                </button>
                                <button
                                    className="w-7 h-7 flex items-center justify-center text-zinc-400 hover:text-zinc-800 hover:bg-zinc-50 transition-all"
                                    title="New Chat"
                                    onClick={() => setMessages([])}
                                >
                                    <FontAwesomeIcon icon={faPlus} className="text-xs" />
                                </button>
                            </div>
                        )}
                    </div>

                    {/* Chat View */}
                    {activeTab === 'chat' && (
                        <>
                            {messages.length === 0 ? (
                                <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-zinc-50/30">
                                    <div className="w-full max-w-[320px] mb-8 opacity-50">
                                        <span className="text-zinc-300 font-semibold text-4xl select-none block mb-2">AI</span>
                                        <p className="text-zinc-400 text-sm">Ask anything about your geometry, manufacturing checks, or cost estimation.</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex-1 overflow-y-auto p-0 flex flex-col bg-white">
                                    {messages.map((msg, idx) => (
                                        <div key={idx} className={`p-6 border-b border-gray-50 flex flex-col gap-2 ${msg.role === 'ai' ? 'bg-zinc-50/50' : 'bg-white'}`}>
                                            <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                                                {msg.role === 'user' ? 'You' : 'Tactile AI'}
                                            </span>
                                            {msg.role === 'ai' ? (
                                                <div className="text-sm text-zinc-800 leading-relaxed prose prose-sm prose-zinc max-w-none prose-p:my-1 prose-strong:text-zinc-900 prose-code:text-xs prose-code:bg-zinc-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-zinc-100 prose-pre:text-xs prose-ul:my-1 prose-li:my-0">
                                                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                                                </div>
                                            ) : (
                                                <div className="text-sm text-zinc-800 leading-relaxed whitespace-pre-wrap">
                                                    {msg.content}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                    {isLoading && (
                                        <div className="p-6 border-b border-gray-50 flex flex-col gap-2 bg-zinc-50/50">
                                            <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                                                Tactile AI
                                            </span>
                                            <div className="flex items-center gap-2 text-sm text-zinc-500">
                                                <FontAwesomeIcon icon={faSpinner} className="animate-spin text-primary" />
                                                <span>Thinking...</span>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            <div className={`p-4 bg-white ${messages.length === 0 ? 'absolute top-1/2 left-0 right-0 -translate-y-1/2 px-8' : 'border-t border-gray-100'}`}>
                                <div className={`relative flex flex-col border border-gray-200 shadow-sm bg-white focus-within:border-zinc-300 focus-within:shadow-md transition-all duration-200 ${isLoading ? 'opacity-60' : ''}`}>
                                    <input
                                        type="text"
                                        className="w-full bg-transparent text-sm p-3 focus:outline-none placeholder:text-zinc-400 disabled:cursor-not-allowed"
                                        placeholder={isLoading ? "Waiting for response..." : messages.length === 0 ? "Ask a question..." : "Reply..."}
                                        value={inputValue}
                                        onChange={(e) => setInputValue(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                                        disabled={isLoading}
                                        autoFocus
                                    />
                                    <div className="flex justify-between items-center px-2 pb-2">
                                        <span className="text-[10px] text-zinc-300 font-medium px-2">CMD + K</span>
                                        <button
                                            onClick={handleSendMessage}
                                            disabled={isLoading}
                                            className={`transition-colors p-1 ${isLoading ? 'text-zinc-300 cursor-not-allowed' : 'text-zinc-400 hover:text-zinc-800'}`}
                                        >
                                            <FontAwesomeIcon icon={faPaperPlane} className="text-xs" />
                                        </button>
                                    </div>
                                </div>

                                {messages.length === 0 && (
                                    <div className="flex gap-2 mt-4 justify-center">
                                        <button className="text-xs text-zinc-500 bg-gray-50 border border-gray-200 px-2 py-1 hover:bg-gray-100 transition-colors">Analyze Wall Thickness</button>
                                        <button className="text-xs text-zinc-500 bg-gray-50 border border-gray-200 px-2 py-1 hover:bg-gray-100 transition-colors">Cost Estimate</button>
                                    </div>
                                )}
                            </div>
                        </>
                    )}

                    {/* Agent Feed View */}
                    {activeTab === 'feed' && (
                        <div className="flex-1 overflow-y-auto bg-zinc-50/30 font-mono">
                            {events.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full text-zinc-400">
                                    <FontAwesomeIcon icon={faBolt} className="mb-2 text-xl opacity-20" />
                                    <span className="text-xs">No events yet</span>
                                </div>
                            ) : (
                                <div className="flex flex-col">
                                    {events.map((event) => (
                                        <div key={event.id} className="p-4 border-b border-gray-100 bg-white hover:bg-gray-50/50 transition-colors flex gap-3">
                                            <div className="mt-1">
                                                {/* Status dot based on type */}
                                                <div className={`w-2 h-2 rounded-full ${event.type === 'ERROR' ? 'bg-red-500' :
                                                    event.type === 'SUCCESS' ? 'bg-green-500' :
                                                        event.type === 'THINKING' ? 'bg-yellow-400' : 'bg-blue-500'
                                                    }`}></div>
                                            </div>
                                            <div className="flex-1 flex flex-col gap-1 min-w-0">
                                                <div className="flex items-center justify-between gap-2">
                                                    <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider truncate">{event.type}</span>
                                                    <span className="text-[10px] text-zinc-300 whitespace-nowrap">{new Date(event.createdAt).toLocaleTimeString()}</span>
                                                </div>
                                                <span className="text-xs font-semibold text-zinc-800 truncate block">{event.title}</span>
                                                {event.content && (
                                                    <p className="text-[11px] text-zinc-500 line-clamp-2 leading-relaxed bg-gray-50 p-2 rounded border border-gray-100 mt-1 font-mono">
                                                        {event.content}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                </div>
            </div>
        </div>
    );
}
