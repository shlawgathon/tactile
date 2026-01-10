package com.shlawgathon.tactile.backend.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.shlawgathon.tactile.backend.dto.PaymentRequirement;
import com.shlawgathon.tactile.backend.dto.UpgradeRequest;
import com.shlawgathon.tactile.backend.dto.UpgradeResponse;
import com.shlawgathon.tactile.backend.dto.UserResponse;
import com.shlawgathon.tactile.backend.model.SubscriptionTier;
import com.shlawgathon.tactile.backend.model.User;
import com.shlawgathon.tactile.backend.service.UserService;
import com.shlawgathon.tactile.backend.service.X402Service;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.web.bind.annotation.*;

import java.util.Base64;

@RestController
@RequestMapping("/api/users")
@Tag(name = "Users", description = "User Management")
public class UserController {

    private final UserService userService;
    private final X402Service x402Service;
    private final ObjectMapper objectMapper;

    public UserController(UserService userService, X402Service x402Service, ObjectMapper objectMapper) {
        this.userService = userService;
        this.x402Service = x402Service;
        this.objectMapper = objectMapper;
    }

    @GetMapping("/me")
    @Operation(summary = "Get current user", description = "Get the authenticated user's profile")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "User profile returned"),
            @ApiResponse(responseCode = "401", description = "Not authenticated")
    })
    public ResponseEntity<UserResponse> getCurrentUser(@AuthenticationPrincipal OAuth2User principal) {
        if (principal == null) {
            return ResponseEntity.status(401).build();
        }

        User user = userService.findOrCreateFromOAuth(principal, "github");
        return ResponseEntity.ok(toUserResponse(user));
    }

    private UserResponse toUserResponse(User user) {
        return UserResponse.builder()
                .id(user.getId())
                .email(user.getEmail())
                .name(user.getName())
                .avatarUrl(user.getAvatarUrl())
                .oauthProvider(user.getOauthProvider())
                .createdAt(user.getCreatedAt())
                .subscriptionTier(user.getSubscriptionTier())
                .usageThisMonth(user.getUsageThisMonth())
                .build();
    }

    @PostMapping("/upgrade")
    @Operation(summary = "Upgrade subscription", description = "Upgrade user subscription tier using x402 payment protocol")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Subscription upgraded successfully"),
            @ApiResponse(responseCode = "402", description = "Payment required - check PAYMENT-REQUIRED header"),
            @ApiResponse(responseCode = "400", description = "Invalid target tier or payment failed"),
            @ApiResponse(responseCode = "401", description = "Not authenticated")
    })
    public ResponseEntity<?> upgradeSubscription(
            @RequestHeader(value = "PAYMENT-SIGNATURE", required = false) String paymentSignature,
            @RequestBody UpgradeRequest request,
            @AuthenticationPrincipal OAuth2User principal) {

        // Check authentication
        if (principal == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }

        User user = userService.findOrCreateFromOAuth(principal, "github");
        SubscriptionTier targetTier = request.getTargetTier();

        // Validate target tier
        if (targetTier == null || targetTier == SubscriptionTier.FREE) {
            return ResponseEntity.badRequest()
                    .body(UpgradeResponse.builder()
                            .success(false)
                            .message("Invalid target tier. Must be PRO or ENTERPRISE.")
                            .build());
        }

        // Check if already at or above target tier
        if (user.getSubscriptionTier().ordinal() >= targetTier.ordinal()) {
            return ResponseEntity.badRequest()
                    .body(UpgradeResponse.builder()
                            .success(false)
                            .newTier(user.getSubscriptionTier())
                            .message("Already at or above requested tier.")
                            .build());
        }

        // If no payment signature, return 402 with payment requirements
        if (paymentSignature == null || paymentSignature.isBlank()) {
            try {
                PaymentRequirement.PaymentRequiredResponse paymentRequired = x402Service
                        .buildPaymentRequiredResponse(targetTier);
                String paymentRequiredJson = objectMapper.writeValueAsString(paymentRequired);
                String paymentRequiredBase64 = Base64.getEncoder().encodeToString(
                        paymentRequiredJson.getBytes());

                return ResponseEntity.status(HttpStatus.PAYMENT_REQUIRED)
                        .header("PAYMENT-REQUIRED", paymentRequiredBase64)
                        .body(paymentRequired);
            } catch (Exception e) {
                return ResponseEntity.internalServerError()
                        .body(UpgradeResponse.builder()
                                .success(false)
                                .message("Failed to build payment requirements: " + e.getMessage())
                                .build());
            }
        }

        // Payment signature provided - verify and settle
        PaymentRequirement requirement = x402Service.buildPaymentRequirement(targetTier);

        // Verify payment
        boolean isValid = x402Service.verifyPayment(paymentSignature, requirement);
        if (!isValid) {
            return ResponseEntity.badRequest()
                    .body(UpgradeResponse.builder()
                            .success(false)
                            .message("Payment verification failed.")
                            .build());
        }

        // Settle payment
        X402Service.SettlementResult settlement = x402Service.settlePayment(paymentSignature, requirement);
        if (!settlement.success()) {
            return ResponseEntity.badRequest()
                    .body(UpgradeResponse.builder()
                            .success(false)
                            .message("Payment settlement failed.")
                            .build());
        }

        // Upgrade user subscription
        User upgradedUser = userService.upgradeSubscription(user.getId(), targetTier);

        return ResponseEntity.ok()
                .header("PAYMENT-RESPONSE", settlement.transactionHash())
                .body(UpgradeResponse.builder()
                        .success(true)
                        .newTier(upgradedUser.getSubscriptionTier())
                        .transactionId(settlement.transactionHash())
                        .message("Successfully upgraded to " + targetTier.name() + " tier!")
                        .build());
    }
}
