'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faUpload, faFileCode, faSpinner, faChevronLeft, faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { Instrument_Sans } from "next/font/google";
import { Job, uploadFile, createJob, getJobs } from '../../services/jobs';

const instrument_sans = Instrument_Sans({
    weight: ["400", "500", "600"],
    subsets: ["latin"],
});

const ITEMS_PER_PAGE = 5;

export default function Dashboard() {
    const [isDragging, setIsDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [jobs, setJobs] = useState<Job[]>([]);
    const [currentPage, setCurrentPage] = useState(1);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const totalPages = Math.ceil(jobs.length / ITEMS_PER_PAGE);
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const paginatedJobs = jobs.slice(startIndex, startIndex + ITEMS_PER_PAGE);

    const fetchJobs = async () => {
        const jobsData = await getJobs();
        setJobs(jobsData);
    };

    useEffect(() => {
        fetchJobs();
    }, []);

    const handleFileUpload = async (files: FileList | null) => {
        if (!files || files.length === 0) return;

        setUploading(true);
        try {
            const file = files[0];
            const fileId = await uploadFile(file);

            if (fileId) {
                await createJob(fileId, file.name);
                await fetchJobs(); // Refresh list
            }
        } catch (error) {
            console.error("Upload process failed", error);
        } finally {
            setUploading(false);
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        handleFileUpload(e.dataTransfer.files);
    };

    const handleClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        handleFileUpload(e.target.files);
    };

    return (
        <div className="w-full min-h-screen flex flex-col gap-8 max-w-4xl mx-auto">
            <div className="flex flex-col tracking-">
                <h1 className={`${instrument_sans.className} text-2xl font-semibold`}>Get Started</h1>
                <p className="text-zinc-500 text-sm">Import your stems to start working</p>
            </div>

            <div
                className={`flex flex-col items-center justify-center w-full h-[300px] border-2 border-dashed transition-all cursor-pointer group relative overflow-hidden
                    ${isDragging ? 'border-primary bg-zinc-50' : 'border-zinc-300 hover:border-zinc-400 bg-white'}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={handleClick}
            >
                {uploading && (
                    <div className="absolute inset-0 bg-white/90 flex flex-col items-center justify-center z-10 backdrop-blur-md">
                        <div className="relative w-10 h-10 mb-3">
                            <div className="absolute inset-0 border-4 border-zinc-100 rounded-full"></div>
                            <div className="absolute inset-0 border-4 border-t-primary border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin"></div>
                        </div>
                        <span className="text-sm font-semibold tracking-wide text-zinc-800">UPLOADING</span>
                        <span className="text-xs text-zinc-400">Processing your file...</span>
                    </div>
                )}

                <input
                    type="file"
                    className="hidden"
                    ref={fileInputRef}
                    accept=".step,.stp"
                    onChange={handleFileChange}
                />

                <div className="w-16 h-16 bg-zinc-50 border border-zinc-200 flex items-center justify-center mb-6 group-hover:scale-105 transition-transform">
                    <FontAwesomeIcon icon={faUpload} className="text-xl text-zinc-400 group-hover:text-black transition-colors" />
                </div>

                <p className="text-zinc-600 font-medium text-lg">Get started by uploading a <span className="font-bold text-white bg-primary px-1 border border-primary">.STEP</span> file</p>
                <p className="text-zinc-400 text-sm mt-2">Drag and drop or click to browse</p>
            </div>

            <div className="flex flex-col gap-4">
                <div className="flex items-center justify-between">
                    <h2 className={`${instrument_sans.className} text-lg font-semibold`}>Recent Jobs</h2>
                    {jobs.length > 0 && (
                        <span className="text-xs text-zinc-400">
                            Showing {startIndex + 1}-{Math.min(startIndex + ITEMS_PER_PAGE, jobs.length)} of {jobs.length}
                        </span>
                    )}
                </div>

                {jobs.length === 0 ? (
                    <div className="w-full py-12 text-center border border-dashed border-zinc-200 bg-gray-50 text-zinc-400 text-sm">
                        No files uploaded yet.
                    </div>
                ) : (
                    <>
                        <div className="flex flex-col border border-gray-200 bg-white shadow-sm">
                            {/* Header */}
                            <div className="grid grid-cols-12 px-6 py-3 border-b border-gray-100 bg-gray-50 text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                                <div className="col-span-5">Filename</div>
                                <div className="col-span-3">Status</div>
                                <div className="col-span-2">Process</div>
                                <div className="col-span-2 text-right">Date</div>
                            </div>

                            {/* Rows */}
                            {paginatedJobs.map((job) => (
                                <Link href={`/jobs/${job.id}`} key={job.id} className="grid grid-cols-12 px-6 py-4 border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors items-center text-sm cursor-pointer no-underline">
                                    <div className="col-span-5 flex items-center gap-3 font-medium text-zinc-800">
                                        <div className="w-8 h-8 flex items-center justify-center bg-gray-100 border border-gray-200 text-zinc-500">
                                            <FontAwesomeIcon icon={faFileCode} className="text-xs" />
                                        </div>
                                        {job.originalFilename}
                                    </div>
                                    <div className="col-span-3 flex items-center gap-2">
                                        <span className="text-zinc-600 capitalize text-xs font-medium bg-gray-100 px-2 py-0.5 border border-gray-200">
                                            {job.status.replace('_', ' ')}
                                        </span>
                                    </div>
                                    <div className="col-span-2 text-zinc-500 text-xs">
                                        {job.manufacturingProcess || "FDM Print"}
                                    </div>
                                    <div className="col-span-2 text-right text-zinc-400 text-xs font-mono">
                                        {new Date(job.createdAt).toLocaleDateString()}
                                    </div>
                                </Link>
                            ))}
                        </div>

                        {/* Pagination Controls */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-center gap-2">
                                <button
                                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                    disabled={currentPage === 1}
                                    className="w-8 h-8 flex items-center justify-center border border-gray-200 bg-white text-zinc-500 hover:bg-gray-50 hover:text-black disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
                                >
                                    <FontAwesomeIcon icon={faChevronLeft} className="text-xs" />
                                </button>

                                {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                                    <button
                                        key={page}
                                        onClick={() => setCurrentPage(page)}
                                        className={`w-8 h-8 flex items-center justify-center border text-xs font-medium transition-colors cursor-pointer
                                            ${currentPage === page
                                                ? 'bg-primary border-primary text-white'
                                                : 'border-gray-200 bg-white text-zinc-600 hover:bg-gray-50 hover:text-black'
                                            }`}
                                    >
                                        {page}
                                    </button>
                                ))}

                                <button
                                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                    disabled={currentPage === totalPages}
                                    className="w-8 h-8 flex items-center justify-center border border-gray-200 bg-white text-zinc-500 hover:bg-gray-50 hover:text-black disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
                                >
                                    <FontAwesomeIcon icon={faChevronRight} className="text-xs" />
                                </button>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}