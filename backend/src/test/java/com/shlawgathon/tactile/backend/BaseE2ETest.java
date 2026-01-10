package com.shlawgathon.tactile.backend;

import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

/**
 * Base class for E2E tests with local MongoDB.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public abstract class BaseE2ETest {

    @DynamicPropertySource
    static void setProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.data.mongodb.uri", () -> "mongodb://localhost:27017");
        registry.add("spring.data.mongodb.database", () -> "tactile-test");
        // Disable OAuth for tests
        registry.add("spring.security.oauth2.client.registration.github.client-id", () -> "test-client-id");
        registry.add("spring.security.oauth2.client.registration.github.client-secret", () -> "test-client-secret");
    }
}
