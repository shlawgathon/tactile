import { http, createConfig } from 'wagmi';
import { baseSepolia, base } from 'wagmi/chains';
import { coinbaseWallet, metaMask, injected } from 'wagmi/connectors';

// USDC contract addresses
export const USDC_ADDRESSES = {
    [baseSepolia.id]: '0x036CbD53842c5426634e7929541eC2318f3dCF7e' as const,
    [base.id]: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as const,
} as const;

export const config = createConfig({
    chains: [baseSepolia, base],
    connectors: [
        coinbaseWallet({
            appName: 'Tactile',
            // Enable smart wallet for better UX
            preference: 'smartWalletOnly',
        }),
        metaMask(),
        injected(),
    ],
    transports: {
        [baseSepolia.id]: http(),
        [base.id]: http(),
    },
});

// Default to Base Sepolia for testnet
export const DEFAULT_CHAIN = baseSepolia;
export const DEFAULT_NETWORK = 'eip155:84532'; // CAIP-2 format for Base Sepolia
