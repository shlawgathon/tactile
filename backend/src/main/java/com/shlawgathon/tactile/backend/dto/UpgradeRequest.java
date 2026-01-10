package com.shlawgathon.tactile.backend.dto;

import com.shlawgathon.tactile.backend.model.SubscriptionTier;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request to upgrade user subscription tier.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Upgrade subscription request")
public class UpgradeRequest {

    @NotNull
    @Schema(description = "Target subscription tier (PRO or ENTERPRISE)", required = true)
    private SubscriptionTier targetTier;
}
