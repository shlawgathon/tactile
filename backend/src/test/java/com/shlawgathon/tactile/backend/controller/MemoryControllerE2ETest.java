package com.shlawgathon.tactile.backend.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.shlawgathon.tactile.backend.BaseE2ETest;
import com.shlawgathon.tactile.backend.dto.QueryMemoryRequest;
import com.shlawgathon.tactile.backend.dto.StoreMemoryRequest;
import com.shlawgathon.tactile.backend.repository.JobMemoryRepository;
import com.shlawgathon.tactile.backend.service.FireworksAIService;
import com.shlawgathon.tactile.backend.service.VoyageEmbeddingService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Collections;
import java.util.Map;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.oauth2Login;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@AutoConfigureMockMvc
class MemoryControllerE2ETest extends BaseE2ETest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private JobMemoryRepository jobMemoryRepository;

    @MockBean
    private VoyageEmbeddingService voyageEmbeddingService;

    @MockBean
    private FireworksAIService fireworksAIService;

    @BeforeEach
    void setUp() throws Exception {
        jobMemoryRepository.deleteAll();
        // Mock embedding service to return dummy vectors
        when(voyageEmbeddingService.generateEmbedding(anyString()))
                .thenReturn(Collections.nCopies(1024, 0.1));
    }

    @Test
    void shouldStoreMemory() throws Exception {
        StoreMemoryRequest request = StoreMemoryRequest.builder()
                .content("The CAD model has an overhang angle of 60 degrees")
                .category("geometry")
                .metadata(Map.of("angle", 60))
                .build();

        mockMvc.perform(post("/internal/jobs/test-job-mem1/memory")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.jobId").value("test-job-mem1"))
                .andExpect(jsonPath("$.category").value("geometry"));
    }

    @Test
    void shouldGetAllMemories() throws Exception {
        // Store multiple memories
        for (int i = 0; i < 3; i++) {
            StoreMemoryRequest request = StoreMemoryRequest.builder()
                    .content("Memory content " + i)
                    .category("geometry")
                    .build();

            mockMvc.perform(post("/internal/jobs/test-job-mem2/memory")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isOk());
        }

        // Get all memories
        mockMvc.perform(get("/internal/jobs/test-job-mem2/memory"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3));
    }

    @Test
    void shouldStoreMemoryWithCategory() throws Exception {
        StoreMemoryRequest request = StoreMemoryRequest.builder()
                .content("Material is ABS plastic")
                .category("material")
                .build();

        mockMvc.perform(post("/internal/jobs/test-job-mem3/memory")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.category").value("material"));
    }

    @Test
    void shouldQueryMemory() throws Exception {
        // Store some memories first
        StoreMemoryRequest request = StoreMemoryRequest.builder()
                .content("The model has thin walls that are 0.5mm thick")
                .category("issue")
                .build();

        mockMvc.perform(post("/internal/jobs/test-job-query/memory")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk());

        // Mock Fireworks AI response
        when(fireworksAIService.chatCompletion(org.mockito.ArgumentMatchers.anyList(),
                org.mockito.ArgumentMatchers.anyInt(),
                org.mockito.ArgumentMatchers.anyDouble()))
                .thenReturn("The model has thin walls at 0.5mm which may cause issues.");

        // Query with OAuth2
        QueryMemoryRequest queryRequest = QueryMemoryRequest.builder()
                .query("What issues were found?")
                .build();

        mockMvc.perform(post("/api/jobs/test-job-query/query")
                .with(oauth2Login()
                        .attributes(attrs -> {
                            attrs.put("id", 12345);
                            attrs.put("login", "testuser");
                        }))
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(queryRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.answer").exists());
    }

    @Test
    void shouldRequireAuthForQueryEndpoint() throws Exception {
        QueryMemoryRequest queryRequest = QueryMemoryRequest.builder()
                .query("What issues were found?")
                .build();

        mockMvc.perform(post("/api/jobs/test-job-auth/query")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(queryRequest)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void shouldAllowInternalMemoryWithoutAuth() throws Exception {
        StoreMemoryRequest request = StoreMemoryRequest.builder()
                .content("Internal memory storage test")
                .category("test")
                .build();

        mockMvc.perform(post("/internal/jobs/test-job-internal/memory")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk());
    }
}
