package com.shlawgathon.tactile.backend.dto;

import com.shlawgathon.tactile.backend.model.SubscriptionTier;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * User response DTO.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "User details response")
public class UserResponse {

    @Schema(description = "User ID")
    private String id;

    @Schema(description = "User email")
    private String email;

    @Schema(description = "User display name")
    private String name;

    @Schema(description = "Avatar URL")
    private String avatarUrl;

    @Schema(description = "OAuth provider (github)")
    private String oauthProvider;

    @Schema(description = "Account creation date")
    private Instant createdAt;

    @Schema(description = "Subscription tier")
    private SubscriptionTier subscriptionTier;

    @Schema(description = "Usage count this month")
    private int usageThisMonth;
}

/**
 * Create user request (for testing/admin).
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Create user request")
class CreateUserRequest {

    @Schema(description = "User email", required = true)
    private String email;

    @Schema(description = "User name")
    private String name;

    @Schema(description = "OAuth provider")
    private String oauthProvider;

    @Schema(description = "OAuth ID")
    private String oauthId;
}
