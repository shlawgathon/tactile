'use client';

import React, { useEffect, useState } from 'react';
import { Instrument_Sans } from "next/font/google";
import { getCurrentUser } from "../../../services/auth";
import { faGithub } from '@fortawesome/free-brands-svg-icons';

const instrument_sans = Instrument_Sans({
    weight: ["400", "500", "600"],
    subsets: ["latin"],
});

export default function PreferencesPage() {
    const [user, setUser] = useState<any>(null);

    useEffect(() => {
        getCurrentUser().then(setUser);
    }, []);

    if (!user) {
        return <div className="animate-pulse flex flex-col gap-8 max-w-4xl mx-auto mt-10">
            <div className="h-8 bg-gray-200 w-1/3"></div>
            <div className="h-40 bg-gray-200 w-full"></div>
        </div>
    }

    return (
        <div className="max-w-4xl mx-auto flex flex-col gap-8">
            <div className="flex flex-col gap-1">
                <h1 className={`${instrument_sans.className} text-2xl font-semibold`}>Account Preferences</h1>
                <p className="text-zinc-500 text-sm">Manage your account settings and preferences.</p>
            </div>

            {/* Profile Card */}
            <div className="bg-white border border-gray-200 p-6 flex flex-col gap-6">
                <div className="flex items-center gap-4 pb-6 border-b border-gray-100">
                    <img
                        src={user.avatarUrl || "https://github.com/identicons/default.png"}
                        alt="Profile"
                        className="w-16 h-16 rounded-none border border-gray-200 object-cover"
                    />
                    <div className="flex flex-col">
                        <h2 className={`text-xl font-medium ${instrument_sans.className}`}>{user.name || 'User'}</h2>
                        <span className="text-zinc-400 text-sm flex items-center gap-1">
                            GitHub Connected
                        </span>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Email Address</label>
                        <div className="flex items-center gap-2 text-sm text-zinc-800">
                            {user.email || "No email visible"}
                        </div>
                    </div>
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">User ID</label>
                        <div className="flex items-center gap-2 text-sm text-zinc-800 font-mono">
                            {user.id}
                        </div>
                    </div>
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Plan</label>
                        <div className="flex items-center gap-2 text-sm text-zinc-800">
                            <span className="bg-primary text-white text-[10px] px-2 py-0.5 font-bold uppercase tracking-wide">
                                {user.subscriptionTier || "FREE"}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Plans Section */}
            <div className="flex flex-col relative pb-20">
                <div className="sticky top-0 bg-gray-50/95 backdrop-blur-sm z-10 py-4 border-b border-gray-200 mb-6 flex items-center justify-between">
                    <h2 className={`${instrument_sans.className} text-lg font-semibold`}>Plans & Pricing</h2>
                    <span className="text-xs text-zinc-500 font-medium px-2 py-1 bg-white border border-gray-200 rounded-sm">Current Plan: {user.subscriptionTier || "FREE"}</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Free Plan */}
                    <div className="flex flex-col bg-white border border-gray-200 border-t-4 border-t-primary p-6 h-full shadow-sm">
                        <h3 className={`${instrument_sans.className} text-xl font-medium mb-1 text-primary`}>Free</h3>
                        <div className="text-3xl font-bold mb-6">$0</div>

                        <div className="flex flex-col gap-3 mb-8 flex-1">
                            <p className="text-sm text-zinc-600">Perfect for getting started.</p>
                            <ul className="text-sm text-zinc-500 space-y-2 mt-2">
                                <li className="flex items-start gap-2">
                                    <span className="text-primary">•</span> 5 Projects
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-primary">•</span> Community Support
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-primary">•</span> Basic Analytics
                                </li>
                            </ul>
                        </div>

                        <button className="text-sm font-medium w-full py-2 border border-gray-200 bg-gray-50 text-zinc-400 cursor-not-allowed">Current Plan</button>
                    </div>

                    {/* Pro Plan */}
                    <div className="flex flex-col bg-white border border-gray-200 border-t-4 border-t-blue-600 p-6 relative shadow-md h-full">
                        <div className="absolute top-0 right-0 bg-blue-600 text-white text-[10px] px-2 py-0.5 font-bold uppercase tracking-wider">Popular</div>
                        <h3 className={`${instrument_sans.className} text-xl font-medium mb-1 text-blue-600`}>Pro</h3>
                        <div className="text-3xl font-bold mb-6">$9.99<span className="text-sm font-normal text-zinc-500">/mo</span></div>

                        <div className="flex flex-col gap-3 mb-8 flex-1">
                            <p className="text-sm text-zinc-600">For power users and creators.</p>
                            <ul className="text-sm text-zinc-500 space-y-2 mt-2">
                                <li className="flex items-start gap-2">
                                    <span className="text-blue-600">•</span> Unlimited Projects
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-blue-600">•</span> Priority Support
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-blue-600">•</span> Advanced Analytics
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-blue-600">•</span> Early Access Features
                                </li>
                            </ul>
                        </div>

                        <button className="cursor-pointer text-sm font-medium w-full py-2 bg-blue-600 text-white hover:bg-blue-700 transition-colors">Upgrade to Pro</button>
                    </div>

                    {/* Enterprise Plan */}
                    <div className="flex flex-col bg-white border border-gray-200 border-t-4 border-t-purple-600 p-6 h-full shadow-sm">
                        <h3 className={`${instrument_sans.className} text-xl font-medium mb-1 text-purple-600`}>Enterprise</h3>
                        <div className="text-3xl font-bold mb-6">$99<span className="text-sm font-normal text-zinc-500">/mo</span></div>

                        <div className="flex flex-col gap-3 mb-8 flex-1">
                            <p className="text-sm text-zinc-600">For large teams and organizations.</p>
                            <ul className="text-sm text-zinc-500 space-y-2 mt-2">
                                <li className="flex items-start gap-2">
                                    <span className="text-purple-600">•</span> SSO & Advanced Security
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-purple-600">•</span> Dedicated Success Manager
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-purple-600">•</span> Custom Contracts
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-purple-600">•</span> Unlimited History
                                </li>
                            </ul>
                        </div>

                        <button className="cursor-pointer text-sm font-medium w-full py-2 border border-purple-600 text-purple-600 hover:bg-purple-50 transition-colors">Upgrade to Enterprise</button>
                    </div>
                </div>
            </div>
        </div>
    );
}
