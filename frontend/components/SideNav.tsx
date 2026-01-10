'use client';

import React, { useEffect, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowUpRightFromSquare, faSignOut, faChevronLeft, faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { logout } from "../services/auth";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Instrument_Sans } from "next/font/google";

const instrument_sans = Instrument_Sans({
    weight: ["400", "500", "600"],
    subsets: ["latin"],
});

interface SideNavProps {
    user: any;
    userData: any;
    title: string;
}

const SideNav = ({ user, userData, title }: SideNavProps) => {
    const router = useRouter();
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(false);

    const linkClasses = (isActive: boolean) =>
        `text-sm font-medium transition-colors ${isActive
            ? 'text-black'
            : 'text-zinc-600 hover:text-black'}`;

    const toggleCollapse = () => setCollapsed(!collapsed);

    return (
        <div
            className={`flex flex-col bg-white border-r border-gray-200 h-screen transition-all duration-300 ease-in-out relative ${collapsed ? 'w-[64px] min-w-[64px]' : 'w-[260px] min-w-[260px]'
                }`}
        >
            <div className={`flex w-full items-center h-14 border-b border-gray-200 ${collapsed ? 'justify-center px-0' : 'px-6'}`}>
                {collapsed ? (
                    <div className={`bg-primary text-white w-8 h-8 flex items-center justify-center text-xs font-bold ${instrument_sans.className}`}>T3D</div>
                ) : (
                    <a href="/" className={`bg-primary text-white py-1 px-4 text-md font-semibold ${instrument_sans.className}`}>tactile3d</a>
                )}
            </div>

            <div className={`flex flex-col w-full border-b border-gray-200 gap-2 ${collapsed ? 'py-4 items-center px-0' : 'px-6 py-5'}`}>
                {!collapsed && <h1 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Jobs</h1>}
                <Link href="/" className={linkClasses(pathname === "/")} title="All Jobs">
                    {collapsed ? "Jobs" : "All Jobs"}
                </Link>
            </div>

            <div className={`flex flex-col w-full border-b border-gray-200 gap-2 ${collapsed ? 'py-4 items-center px-0' : 'px-6 py-5'}`}>
                {!collapsed && <h1 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Account</h1>}
                <Link href="/preferences" className={linkClasses(pathname === "/preferences")} title="Preferences">
                    {collapsed ? "Prefs" : "Preferences"}
                </Link>
            </div>

            {!collapsed &&
                (
                    <div className={`flex flex-col w-full border-b border-gray-200 gap-2 px-6 py-5`}>
                        <h1 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Documentation</h1>
                        <Link href="/guides" className="text-sm tracking-wide font-medium text-zinc-600 hover:text-black flex items-center" title="Guides">
                            <FontAwesomeIcon icon={faArrowUpRightFromSquare} className="mr-2 text-xs" />
                            Guides
                        </Link>
                        <Link href="/api-reference" className="text-sm tracking-wide font-medium text-zinc-600 hover:text-black flex items-center" title="API Reference">
                            <FontAwesomeIcon icon={faArrowUpRightFromSquare} className="mr-2 text-xs" />
                            API Reference
                        </Link>
                    </div>
                )
            }

            <div className={`mt-auto p-4 border-t border-gray-200 flex ${collapsed ? 'justify-center' : 'justify-start'}`}>
                <button
                    onClick={toggleCollapse}
                    className={`cursor-pointer flex items-center text-zinc-400 hover:text-black transition-colors ${collapsed ? 'justify-center w-8 h-8 hover:bg-gray-100 rounded' : 'gap-2 text-sm font-medium'}`}
                    title={collapsed ? "Expand" : "Collapse"}
                >
                    <FontAwesomeIcon icon={collapsed ? faChevronRight : faChevronLeft} className="text-xs" />
                    {!collapsed && "Collapse"}
                </button>
            </div>
        </div>
    );
};

export default SideNav;
