package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.BaseE2ETest;
import com.shlawgathon.tactile.backend.model.SubscriptionTier;
import com.shlawgathon.tactile.backend.model.User;
import com.shlawgathon.tactile.backend.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import static org.junit.jupiter.api.Assertions.*;

class UserServiceE2ETest extends BaseE2ETest {

    @Autowired
    private UserService userService;

    @Autowired
    private UserRepository userRepository;

    @BeforeEach
    void setUp() {
        userRepository.deleteAll();
    }

    @Test
    void shouldSaveAndFindUser() {
        // Given
        User user = User.builder()
                .email("test@example.com")
                .name("Test User")
                .oauthProvider("github")
                .oauthId("12345")
                .subscriptionTier(SubscriptionTier.FREE)
                .build();

        // When
        User savedUser = userService.save(user);

        // Then
        assertNotNull(savedUser.getId());
        assertEquals("test@example.com", savedUser.getEmail());

        // Find by ID
        var found = userService.findById(savedUser.getId());
        assertTrue(found.isPresent());
        assertEquals("Test User", found.get().getName());
    }

    @Test
    void shouldFindByEmail() {
        // Given
        User user = User.builder()
                .email("unique@example.com")
                .name("Unique User")
                .oauthProvider("github")
                .oauthId("67890")
                .build();
        userService.save(user);

        // When
        var found = userService.findByEmail("unique@example.com");

        // Then
        assertTrue(found.isPresent());
        assertEquals("Unique User", found.get().getName());
    }

    @Test
    void shouldIncrementUsage() {
        // Given
        User user = User.builder()
                .email("usage@example.com")
                .name("Usage User")
                .oauthProvider("github")
                .oauthId("usage123")
                .usageThisMonth(5)
                .build();
        User savedUser = userService.save(user);

        // When
        userService.incrementUsage(savedUser.getId());

        // Then
        var updated = userService.findById(savedUser.getId());
        assertTrue(updated.isPresent());
        assertEquals(6, updated.get().getUsageThisMonth());
    }

    @Test
    void shouldDeleteUser() {
        // Given
        User user = User.builder()
                .email("delete@example.com")
                .name("Delete User")
                .oauthProvider("github")
                .oauthId("delete123")
                .build();
        User savedUser = userService.save(user);

        // When
        userService.delete(savedUser.getId());

        // Then
        var found = userService.findById(savedUser.getId());
        assertFalse(found.isPresent());
    }
}
