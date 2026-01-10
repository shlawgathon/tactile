'use client';

import React, { useEffect, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowUpRightFromSquare, faSignOut } from "@fortawesome/free-solid-svg-icons";
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

    const linkClasses = (isActive: boolean) =>
        isActive
            ? 'text-sm font-medium text-black'
            : 'text-sm font-medium text-zinc-600 hover:text-black';

    return (
        <div className="w-[260px] min-w-[260px] h-screen flex flex-col bg-white border-r border-gray-200">
            <div className="flex w-full items-center px-6 h-14 border-b border-gray-200">
                {/* <h1 className={`${instrument_sans.className} font-semibold text-md tracking-tight`}>{title}</h1> */}
                <a href="/" className={`bg-primary text-white py-1 px-4 text-md font-semibold ${instrument_sans.className}`}>tacticle3d</a>
            </div>

            <div className="flex flex-col w-full justify-center px-6 py-5 border-b border-gray-200 gap-2">
                <h1 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Jobs</h1>
                <Link href="/" className={linkClasses(pathname === "/")}>
                    All Jobs
                </Link>
                {/* {projects.map(project => {
                    const href = `/project/${project.id}`;
                    return (
                        <Link key={project.id} href={href} className={linkClasses(pathname === href)}>
                            {project.name}
                        </Link>
                    );
                })} */}
            </div>

            <div className="flex flex-col w-full justify-center px-6 py-5 border-b border-gray-200 gap-2">
                <h1 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Account</h1>
                <Link href="/preferences" className={linkClasses(pathname === "/preferences")}>Preferences</Link>
            </div>

            <div className="flex flex-col w-full justify-center px-6 py-5 border-b border-gray-200 gap-2">
                <h1 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Documentation</h1>
                <Link href="/guides" className="text-sm tracking-wide font-medium text-zinc-600 hover:text-black flex items-center">
                    <FontAwesomeIcon icon={faArrowUpRightFromSquare} className="mr-2 text-xs" />
                    Guides
                </Link>
                <Link href="/api-reference" className="text-sm tracking-wide font-medium text-zinc-600 hover:text-black flex items-center">
                    <FontAwesomeIcon icon={faArrowUpRightFromSquare} className="mr-2 text-xs" />
                    API Reference
                </Link>
            </div>
        </div>
    );
};

export default SideNav;
