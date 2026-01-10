'use client';

import { useMemo, useCallback } from 'react';
import { useWalletClient, useAccount, useConnect } from 'wagmi';
import { x402Client, wrapFetchWithPayment, x402HTTPClient } from '@x402/fetch';
import { registerExactEvmScheme } from '@x402/evm/exact/client';
import type { ClientEvmSigner } from '@x402/evm';
import type { WalletClient, Account } from 'viem';
import { DEFAULT_NETWORK } from '../providers/wagmi-config';

/**
 * Converts a wagmi/viem WalletClient to a ClientEvmSigner for x402Client.
 * This adapter allows the x402 SDK to use the connected wallet for signing.
 */
function wagmiToClientSigner(walletClient: WalletClient): ClientEvmSigner {
    if (!walletClient.account) {
        throw new Error('Wallet not connected');
    }

    const account = walletClient.account as Account;

    return {
        address: account.address,
        signTypedData: async (typedData) => {
            // x402 uses EIP-712 typed data signing for EIP-3009
            const signature = await walletClient.signTypedData({
                account: account.address,
                domain: typedData.domain,
                types: typedData.types,
                primaryType: typedData.primaryType,
                message: typedData.message,
            });
            return signature;
        },
    };
}

/**
 * Hook to use x402 payment functionality with the connected wallet.
 * 
 * Returns:
 * - isConnected: Whether a wallet is connected
 * - address: The connected wallet address
 * - connect: Function to connect a wallet
 * - fetchWithPayment: Fetch wrapper that automatically handles x402 payments
 * - getPaymentResponse: Get the payment settlement response from headers
 */
export function useX402Payment() {
    const { data: walletClient, isLoading: isWalletLoading } = useWalletClient();
    const { address, isConnected } = useAccount();
    const { connect, connectors, isPending: isConnecting } = useConnect();

    // Create x402 client and register EVM scheme when wallet is connected
    const { fetchWithPayment, httpClient } = useMemo(() => {
        if (!walletClient) {
            return { fetchWithPayment: null, httpClient: null };
        }

        try {
            const signer = wagmiToClientSigner(walletClient);
            const client = new x402Client();

            // Register the EVM exact scheme for Base Sepolia
            registerExactEvmScheme(client, { signer });

            // Create wrapped fetch that handles payments
            const wrappedFetch = wrapFetchWithPayment(fetch, client);
            const http = new x402HTTPClient(client);

            return { fetchWithPayment: wrappedFetch, httpClient: http };
        } catch (error) {
            console.error('Failed to initialize x402 client:', error);
            return { fetchWithPayment: null, httpClient: null };
        }
    }, [walletClient]);

    /**
     * Get the payment settlement response from headers after a successful x402 request.
     */
    const getPaymentResponse = useCallback((response: Response) => {
        if (!httpClient) return null;
        return httpClient.getPaymentSettleResponse((name) => response.headers.get(name));
    }, [httpClient]);

    /**
     * Helper to trigger wallet connection with any available connector.
     */
    const connectWallet = useCallback(() => {
        console.log('Available connectors:', connectors.map(c => ({ id: c.id, name: c.name })));

        // Try connectors in order of preference
        const preferredOrder = ['coinbaseWalletSDK', 'metaMaskSDK', 'injected'];

        for (const preferred of preferredOrder) {
            const connector = connectors.find(c =>
                c.id.toLowerCase().includes(preferred.toLowerCase()) ||
                c.name.toLowerCase().includes(preferred.toLowerCase())
            );
            if (connector) {
                console.log('Connecting with:', connector.id, connector.name);
                connect({ connector });
                return;
            }
        }

        // Fallback to first available connector
        if (connectors.length > 0) {
            console.log('Fallback connecting with:', connectors[0].id, connectors[0].name);
            connect({ connector: connectors[0] });
        } else {
            console.error('No connectors available');
        }
    }, [connect, connectors]);

    return {
        // Wallet state
        isConnected,
        isLoading: isWalletLoading || isConnecting,
        address,
        connectors,

        // Wallet actions
        connect: connectWallet,

        // x402 payment functionality
        fetchWithPayment,
        getPaymentResponse,

        // Network info
        network: DEFAULT_NETWORK,
    };
}

/**
 * Upgrade subscription using x402 payment.
 * This function handles the full flow:
 * 1. Initial request (no payment)
 * 2. If 402 returned, x402 SDK auto-signs and retries with payment
 */
export async function upgradeWithX402(
    fetchWithPayment: typeof fetch,
    targetTier: 'PRO' | 'ENTERPRISE',
    apiUrl: string
): Promise<{ success: boolean; data: unknown; paymentResponse?: unknown }> {
    try {
        const response = await fetchWithPayment(`${apiUrl}/users/upgrade`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ targetTier }),
            credentials: 'include',
        });

        const data = await response.json();

        if (response.ok) {
            // Get payment response from headers if present
            const paymentHeader = response.headers.get('PAYMENT-RESPONSE');
            return {
                success: true,
                data,
                paymentResponse: paymentHeader ? JSON.parse(atob(paymentHeader)) : undefined
            };
        }

        return { success: false, data };
    } catch (error) {
        console.error('x402 upgrade failed:', error);
        throw error;
    }
}
