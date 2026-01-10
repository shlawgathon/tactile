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
    projects: any[];
    title: string;
}

const SideNav = ({ user, userData, projects, title }: SideNavProps) => {
    const router = useRouter();
    const pathname = usePathname();

    const handleLogout = async () => {
        await logout();
        router.push('/login');
    };

    const linkClasses = (isActive: boolean) =>
        isActive
            ? 'text-sm font-medium text-black'
            : 'text-sm font-medium text-zinc-600 hover:text-black';

    return (
        <div className="w-[260px] min-w-[260px] h-screen flex flex-col bg-white border-r border-gray-200">
            <div className="flex w-full items-center px-6 h-14 border-b border-gray-200">
                {/* <h1 className={`${instrument_sans.className} font-semibold text-md tracking-tight`}>{title}</h1> */}
                <h1 className={`bg-primary text-white py-1 px-4 text-md font-semibold ${instrument_sans.className}`}>tacticle3d</h1>
            </div>

            <div className="flex flex-col w-full justify-center px-6 py-5 border-b border-gray-200 gap-2">
                <h1 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Projects</h1>
                <Link href="/dashboard" className={linkClasses(pathname === "/dashboard")}>
                    All Projects
                </Link>
                {projects.map(project => {
                    const href = `/project/${project.id}`;
                    return (
                        <Link key={project.id} href={href} className={linkClasses(pathname === href)}>
                            {project.name}
                        </Link>
                    );
                })}
            </div>

            {/* {Array.isArray(orgs) && orgs.length > 0 && (
                <div className="flex flex-col w-full justify-center px-6 py-5 border-b border-gray-200 gap-2">
                    <h1 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Organizations</h1>
                    {orgs.map(org => {
                        const href = `/orgs/${org.id}`;
                        return (
                            <Link key={org.id} href={href} className={linkClasses(pathname === href)}>
                                {org.name}
                            </Link>
                        );
                    })}
                </div>
            )} */}

            {/* {Array.isArray(invites) && invites.length > 0 && (
                <div className="flex flex-col w-full justify-center px-6 py-5 border-b border-gray-200 gap-2">
                    <div className="flex flex-row items-center gap-2 mb-1">
                        <h1 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Invites</h1>
                        <div className="rounded-none bg-red-500 text-white text-[10px] px-1 font-bold h-4 flex items-center justify-center">{invites.length}</div>
                    </div>
                    {invites.map(invite => (
                        <Link key={invite.id} href={`/invite/${invite.id}`} className="text-sm tracking-wide font-medium text-zinc-600 hover:text-black">
                            {invite.orgName}
                        </Link>
                    ))}
                </div>
            )} */}

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

            {/* <div className="flex flex-col w-full justify-center px-6 py-5 border-b border-gray-200 gap-2 mt-auto">
                <button onClick={handleLogout} className="flex flex-row text-sm items-center text-zinc-500 hover:text-black hover:cursor-pointer transition-colors">
                    <FontAwesomeIcon icon={faSignOut} className="mr-3" />
                    <p>Log out</p>
                </button>
            </div> */}
        </div>
    );
};

export default SideNav;
