'use client';

import React, { useState, useRef } from 'react';
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { Instrument_Sans } from "next/font/google";

const instrument_sans = Instrument_Sans({
    weight: ["400", "500", "600"],
    subsets: ["latin"],
});

export default function Dashboard() {
    const [isDragging, setIsDragging] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

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
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            console.log("Files dropped:", files);
            // Handle file upload logic here
        }
    };

    const handleClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files && files.length > 0) {
            console.log("Files selected:", files);
            // Handle file upload logic here
        }
    };

    return (
        <div className="w-full h-full flex flex-col gap-6">
            <div className="flex flex-col tracking-">
                <h1 className={`${instrument_sans.className} text-2xl font-semibold`}>Get Started</h1>
                <p className="text-zinc-500 text-sm">Import your stems to start working</p>
            </div>

            <div
                className={`flex flex-col items-center justify-center w-full h-[400px] border-2 border-dashed transition-all cursor-pointer group
                    ${isDragging ? 'border-primary bg-zinc-50' : 'border-zinc-300 hover:border-zinc-400 bg-white'}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={handleClick}
            >
                <input
                    type="file"
                    className="hidden"
                    ref={fileInputRef}
                    accept=".stem"
                    onChange={handleFileChange}
                />

                <div className="w-16 h-16 bg-zinc-50 border border-zinc-200 flex items-center justify-center mb-6 group-hover:scale-105 transition-transform">
                    <FontAwesomeIcon icon={faUpload} className="text-xl text-zinc-400 group-hover:text-black transition-colors" />
                </div>

                <p className="text-zinc-600 font-medium text-lg">Get started by uploading a <span className="font-bold text-white bg-primary px-1 border border-primary">.STEM</span> file</p>
                <p className="text-zinc-400 text-sm mt-2">Drag and drop or click to browse</p>
            </div>
        </div>
    );
}