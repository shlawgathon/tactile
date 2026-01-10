'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowLeft, faSpinner, faDownload, faPaperPlane, faPlus, faHistory } from "@fortawesome/free-solid-svg-icons";
import { Instrument_Sans } from "next/font/google";
import { getJob, getFileUrl, Job } from '../../../../services/jobs';
import StepViewer from '../../../../components/StepViewer';

const instrument_sans = Instrument_Sans({
    weight: ["400", "500", "600"],
    subsets: ["latin"],
});

export default function JobPage() {
    const params = useParams();
    const id = params?.id as string;
    const [job, setJob] = useState<Job | null>(null);
    const [loading, setLoading] = useState(true);

    // Chat state
    const [messages, setMessages] = useState<{ role: 'user' | 'ai', content: string }[]>([]);
    const [inputValue, setInputValue] = useState('');

    useEffect(() => {
        if (id) {
            getJob(id).then(data => {
                setJob(data);
                setLoading(false);
            });
        }
    }, [id]);

    const handleSendMessage = () => {
        if (!inputValue.trim()) return;
        setMessages([...messages, { role: 'user', content: inputValue }]);
        setInputValue('');

        // Mock response
        setTimeout(() => {
            setMessages(prev => [...prev, { role: 'ai', content: "I'm currently in read-only mode, but I can see your message!" }]);
        }, 1000);
    };

    if (loading) {
        return (
            <div className="w-full h-full flex items-center justify-center bg-zinc-50">
                <FontAwesomeIcon icon={faSpinner} className="text-3xl text-primary animate-spin" />
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
            {/* Top Bar / Data Nav */}
            <div className={`h-14 border-b border-gray-200 bg-white flex items-center justify-between px-4 shrink-0 z-20 ${instrument_sans.className}`}>
                <div className="flex items-center gap-4 overflow-hidden">
                    <Link href="/" className="flex items-center justify-center w-8 h-8 rounded hover:bg-zinc-100 text-zinc-500 transition-colors">
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

                <div className="flex items-center gap-3">
                    <a
                        href={getFileUrl(job.fileStorageId)}
                        className="bg-zinc-100 text-zinc-700 px-3 py-1.5 text-xs font-medium hover:bg-zinc-200 transition-colors flex items-center gap-2 border border-zinc-200"
                        download
                    >
                        <FontAwesomeIcon icon={faDownload} />
                        Download
                    </a>
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

                {/* Right: AI Chat */}
                <div className="w-[400px] bg-white border-l border-gray-200 flex flex-col shrink-0 relative z-10 shadow-xl">

                    {/* Messages Area - changes based on content */}
                    {messages.length === 0 ? (
                        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-zinc-50/30">
                            {/* Placeholder / Empty State */}
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
                                    <div className="text-sm text-zinc-800 leading-relaxed whitespace-pre-wrap">
                                        {msg.content}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Input Area - Fixed at bottom */}
                    <div className={`p-4 bg-white ${messages.length === 0 ? 'absolute top-1/2 left-0 right-0 -translate-y-1/2 px-8' : 'border-t border-gray-100'}`}>
                        <div className="relative flex flex-col border border-gray-200 shadow-sm bg-white focus-within:border-zinc-300 focus-within:shadow-md transition-all duration-200">
                            <input
                                type="text"
                                className="w-full bg-transparent text-sm p-3 focus:outline-none placeholder:text-zinc-400"
                                placeholder={messages.length === 0 ? "Ask a question..." : "Reply..."}
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                                autoFocus
                            />
                            <div className="flex justify-between items-center px-2 pb-2">
                                <span className="text-[10px] text-zinc-300 font-medium px-2">CMD + K</span>
                                <button
                                    onClick={handleSendMessage}
                                    className="text-zinc-400 hover:text-zinc-800 transition-colors p-1"
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
                </div>
            </div>
        </div>
    );
}
