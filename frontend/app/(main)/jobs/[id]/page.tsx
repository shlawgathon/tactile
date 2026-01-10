'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowLeft, faSpinner, faDownload } from "@fortawesome/free-solid-svg-icons";
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

    useEffect(() => {
        if (id) {
            getJob(id).then(data => {
                setJob(data);
                setLoading(false);
            });
        }
    }, [id]);

    if (loading) {
        return (
            <div className="w-full h-full flex items-center justify-center p-12">
                <FontAwesomeIcon icon={faSpinner} className="text-3xl text-primary animate-spin" />
            </div>
        );
    }

    if (!job) {
        return (
            <div className="flex flex-col items-center justify-center w-full h-full gap-4 p-12">
                <p className="text-zinc-500">Job not found.</p>
                <Link href="/" className="text-primary hover:underline">Go back home</Link>
            </div>
        );
    }

    return (
        <div className="w-full flex flex-col gap-6 p-6">
            {/* Header */}
            <div className="flex flex-col gap-4 border-b border-gray-200 pb-6">
                <Link href="/" className="flex items-center gap-2 text-zinc-500 hover:text-zinc-800 transition-colors w-fit text-sm font-medium">
                    <FontAwesomeIcon icon={faArrowLeft} />
                    Back to Dashboard
                </Link>

                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h1 className={`${instrument_sans.className} text-2xl font-semibold`}>{job.originalFilename}</h1>
                        <p className="text-zinc-500 text-sm mt-1">Job ID: {job.id}</p>
                    </div>

                    <div className="flex items-center gap-3">
                        <span className="text-zinc-600 capitalize text-sm font-medium bg-gray-100 px-3 py-1 border border-gray-200">
                            {job.status.replace('_', ' ')}
                        </span>
                        {/* Download original file button */}
                        <a
                            href={getFileUrl(job.fileStorageId)}
                            className="bg-zinc-900 text-white px-4 py-2 text-sm font-medium hover:bg-zinc-800 transition-colors flex items-center gap-2"
                            download
                        >
                            <FontAwesomeIcon icon={faDownload} />
                            Download
                        </a>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Main Viewer */}
                <div className="lg:col-span-2 h-[600px] border border-gray-200 overflow-hidden bg-zinc-50 relative shadow-sm">
                    {/* Viewer Title Overlay */}
                    <div className="absolute top-4 left-4 z-10 bg-white/90 backdrop-blur-sm px-3 py-1.5 border border-gray-200/50 shadow-sm">
                        <span className="text-xs font-semibold text-zinc-600 uppercase tracking-wider">3D Preview</span>
                    </div>

                    {job.fileStorageId ? (
                        <StepViewer url={getFileUrl(job.fileStorageId)} />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center text-zinc-400 text-sm">
                            No file available for preview
                        </div>
                    )}
                </div>

                {/* Details Sidebar */}
                <div className="flex flex-col gap-4">
                    <div className="p-6 bg-white border border-gray-200 flex flex-col gap-4 shadow-sm">
                        <h3 className="font-semibold text-zinc-800 border-b border-gray-100 pb-2">Job Details</h3>

                        <div className="flex flex-col gap-1">
                            <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">Manufacturing Process</span>
                            <span className="text-sm text-zinc-800">{job.manufacturingProcess}</span>
                        </div>

                        <div className="flex flex-col gap-1">
                            <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">Material</span>
                            <span className="text-sm text-zinc-800">PLA (Default)</span>
                        </div>

                        <div className="flex flex-col gap-1">
                            <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">Created At</span>
                            <span className="text-sm text-zinc-800">{new Date(job.createdAt).toLocaleString()}</span>
                        </div>

                        <div className="flex flex-col gap-1">
                            <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">File Storage ID</span>
                            <div className="text-xs text-zinc-500 font-mono break-all bg-gray-50 p-2 rounded border border-gray-100">{job.fileStorageId}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
