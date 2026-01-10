package com.shlawgathon.tactile.backend.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

/**
 * User document for the platform.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "users")
public class User {

    @Id
    private String id;

    @Indexed(unique = true)
    private String email;

    private String name;

    private String avatarUrl;

    private String oauthProvider;

    @Indexed(unique = true)
    private String oauthId;

    @CreatedDate
    private Instant createdAt;

    @Builder.Default
    private SubscriptionTier subscriptionTier = SubscriptionTier.FREE;

    @Builder.Default
    private int usageThisMonth = 0;
}
