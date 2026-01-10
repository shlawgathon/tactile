'use client';

import React from 'react';
import { WagmiProvider as WagmiProviderBase } from 'wagmi';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { config } from './wagmi-config';

// Create a client for React Query
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            // Prevent aggressive refetching
            staleTime: 1000 * 60, // 1 minute
            refetchOnWindowFocus: false,
        },
    },
});

interface WagmiProviderProps {
    children: React.ReactNode;
}

export function WagmiProvider({ children }: WagmiProviderProps) {
    return (
        <WagmiProviderBase config={config}>
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        </WagmiProviderBase>
    );
}
