'use client';

import React, { useState, useRef, useEffect } from 'react';
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChevronDown, faUser, faSignOut, faCog } from "@fortawesome/free-solid-svg-icons";
import { logout } from "../services/auth";
import { useRouter } from "next/navigation";
import Link from "next/link";

interface TopNavProps {
    user?: any;
}

const TopNav = ({ user }: TopNavProps) => {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const router = useRouter();

    const handleLogout = async () => {
        await logout();
        router.push('/login');
    };

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    return (
        <div className="w-full h-14 border-b border-gray-200 bg-white flex items-center justify-between px-6 z-10 relative">
            <div className="flex items-center gap-4">
                <span className="text-sm font-medium text-zinc-500">Projects</span>
            </div>

            <div className="flex items-center gap-3 relative" ref={dropdownRef}>
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className={`cursor-pointer group flex items-center gap-3 bg-gray-50 pl-3 pr-2 py-1.5 border border-gray-200 transition-all outline-none ${isOpen ? 'bg-gray-100 text-black border-gray-300' : 'text-zinc-700'}`}
                >
                    <span className="text-sm font-medium">{user?.email || 'User'}</span>
                    <FontAwesomeIcon icon={faChevronDown} className={`text-[10px] text-zinc-400 group-hover:text-zinc-600 transition-colors ${isOpen ? 'rotate-180' : ''}`} />
                </button>

                {isOpen && (
                    <div className="absolute top-full right-0 mt-1 w-48 bg-white border border-gray-200 shadow-sm flex flex-col py-1 z-50">
                        <Link
                            href="/preferences"
                            className="cursor-pointer px-4 py-2.5 text-sm text-zinc-600 hover:text-black hover:bg-gray-50 flex items-center gap-3 transition-colors"
                            onClick={() => setIsOpen(false)}
                        >
                            <FontAwesomeIcon icon={faCog} className="text-xs text-zinc-400" />
                            Preferences
                        </Link>
                        <div className="h-px bg-gray-100 w-full my-1"></div>
                        <button
                            onClick={() => {
                                handleLogout();
                                setIsOpen(false);
                            }}
                            className="cursor-pointer px-4 py-2.5 text-sm text-zinc-600 hover:text-black hover:bg-gray-50 flex items-center gap-3 text-left w-full transition-colors"
                        >
                            <FontAwesomeIcon icon={faSignOut} className="text-xs text-zinc-400" />
                            Log out
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default TopNav;
