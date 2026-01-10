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

    @Schema(description = "Token asset (e.g., 'USDC')")
    private String asset;

    @Schema(description = "Human-readable description of what the payment is for")
    private String description;

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
