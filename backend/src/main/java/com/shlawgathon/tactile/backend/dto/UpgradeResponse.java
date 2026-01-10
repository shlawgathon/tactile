package com.shlawgathon.tactile.backend.dto;

import com.shlawgathon.tactile.backend.model.SubscriptionTier;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Response for subscription upgrade.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Upgrade subscription response")
public class UpgradeResponse {

    @Schema(description = "Whether the upgrade was successful")
    private boolean success;

    @Schema(description = "New subscription tier after upgrade")
    private SubscriptionTier newTier;

    @Schema(description = "Payment transaction ID from x402 settlement")
    private String transactionId;

    @Schema(description = "Human-readable message")
    private String message;
}
