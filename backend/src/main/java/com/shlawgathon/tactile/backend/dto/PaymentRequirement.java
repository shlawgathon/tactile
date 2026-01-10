package com.shlawgathon.tactile.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * x402 payment requirement for HTTP 402 response.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "x402 payment requirement")
public class PaymentRequirement {

    @Schema(description = "Payment scheme (e.g., 'exact')")
    private String scheme;

    @Schema(description = "Blockchain network identifier (e.g., 'eip155:84532' for Base Sepolia)")
    private String network;

    @Schema(description = "Price in USD format (e.g., '$10.00')")
    private String price;

    @Schema(description = "Wallet address to receive payment")
    private String payTo;

    @Schema(description = "Token asset contract address")
    private String asset;

    @Schema(description = "Maximum amount required in smallest token units (e.g., '10000000' for 10 USDC)")
    private String maxAmountRequired;
    @Schema(description = "Human-readable description of what the payment is for")
    private String description;

    // EIP-712 domain parameters required for EIP-3009 signing
    @Schema(description = "Token contract name for EIP-712 domain (e.g., 'USD Coin')")
    private String name;

    @Schema(description = "Token contract version for EIP-712 domain (e.g., '2')")
    private String version;

    @Schema(description = "Extra parameters for the payment scheme")
    private Extra extra;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Extra {
        private String name;
        private String version;
    }

    /**
     * Wrapper for x402 PAYMENT-REQUIRED header format.
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PaymentRequiredResponse {
        private int x402Version;
        private List<PaymentRequirement> accepts;
        private String error;
    }
}
