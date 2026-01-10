const API_URL = 'http://localhost:8080/api';

export interface UpgradeResponse {
    success: boolean;
    newTier?: string;
    transactionId?: string;
    message?: string;
}

export interface PaymentRequirement {
    scheme: string;
    network: string;
    price: string;
    payTo: string;
    asset: string;
    description: string;
}

export interface PaymentRequiredResponse {
    x402Version: number;
    accepts: PaymentRequirement[];
}

export const upgradeSubscription = async (targetTier: 'PRO' | 'ENTERPRISE', paymentSignature?: string): Promise<{
    status: number;
    data: UpgradeResponse | PaymentRequiredResponse;
    paymentRequiredRaw?: string; // The base64 header
}> => {
    try {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };

        if (paymentSignature) {
            headers['PAYMENT-SIGNATURE'] = paymentSignature;
        }

        const response = await fetch(`${API_URL}/users/upgrade`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ targetTier }),
            credentials: 'include',
        });

        if (response.status === 402) {
            const paymentHeader = response.headers.get('PAYMENT-REQUIRED');
            const data = await response.json();
            return {
                status: 402,
                data: data as PaymentRequiredResponse,
                paymentRequiredRaw: paymentHeader || undefined
            };
        }

        const data = await response.json();
        return {
            status: response.status,
            data: data as UpgradeResponse
        };

    } catch (error) {
        console.error("Upgrade error:", error);
        throw error;
    }
};
