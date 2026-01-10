'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from "next/navigation";
import { DM_Mono } from "next/font/google";
import SideNav from "./SideNav";
import TopNav from "./TopNav";
import { getCurrentUser } from "../services/auth";

const dm_mono = DM_Mono({
    weight: ["300", "400", "500"],
    subsets: ["latin"],
});

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        const fetchUser = async () => {
            try {
                const userData = await getCurrentUser();
                if (!userData) {
                    router.push('/login');
                } else {
                    setUser(userData);
                }
            } catch (error) {
                router.push('/login');
            } finally {
                setLoading(false);
            }
        };

        fetchUser();
    }, [router]);

    return (
        <div className={`${dm_mono.className} flex h-screen w-full bg-white text-black font-sans selection:bg-zinc-200 overflow-hidden`}>
            <SideNav user={user || {}} userData={{}} title="Tactile" />
            <div className="flex flex-col flex-1 h-full min-w-0">
                <TopNav user={user || {}} />
                <main className="flex-1 overflow-y-auto bg-gray-50 p-6 scrollbar-thin scrollbar-thumb-zinc-300 scrollbar-track-transparent">
                    {user ? children : null}
                </main>
            </div>
        </div>
    );
}
