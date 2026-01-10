'use client';

import React from 'react';
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChevronDown, faUser } from "@fortawesome/free-solid-svg-icons";

interface TopNavProps {
    user?: any;
}

const TopNav = ({ user }: TopNavProps) => {
    return (
        <div className="w-full h-14 border-b border-gray-200 bg-white flex items-center justify-between px-6 z-10 relative">
            <div className="flex items-center gap-4">
                <span className="text-sm font-medium text-zinc-500">Dashboard</span>
            </div>

            <div className="flex items-center gap-3">
                <button className="cursor-pointer group flex items-center gap-3 bg-gray-50 pl-3 pr-2 py-1.5 border border-gray-200 transition-all outline-none">
                    <span className="text-sm font-medium text-zinc-700">{user?.email || 'User'}</span>
                    <FontAwesomeIcon icon={faChevronDown} className="text-[10px] text-zinc-400 group-hover:text-zinc-600 transition-colors" />
                </button>
            </div>
        </div>
    );
};

export default TopNav;
