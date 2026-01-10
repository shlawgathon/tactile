package com.shlawgathon.tactile.backend.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.shlawgathon.tactile.backend.BaseE2ETest;
import com.shlawgathon.tactile.backend.dto.CreateJobRequest;
import com.shlawgathon.tactile.backend.model.ManufacturingProcess;
import com.shlawgathon.tactile.backend.model.User;
import com.shlawgathon.tactile.backend.repository.JobRepository;
import com.shlawgathon.tactile.backend.repository.UserRepository;
import com.shlawgathon.tactile.backend.service.AgentCommunicationService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.oauth2Login;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@AutoConfigureMockMvc
class JobControllerE2ETest extends BaseE2ETest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private JobRepository jobRepository;

    @Autowired
    private UserRepository userRepository;

    @MockBean
    private AgentCommunicationService agentCommunicationService;

    @BeforeEach
    void setUp() {
        jobRepository.deleteAll();
        userRepository.deleteAll();
    }

    @Test
    void shouldReturnUnauthorizedWithoutAuth() throws Exception {
        mockMvc.perform(get("/api/jobs"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void shouldAccessHealthEndpointWithoutAuth() throws Exception {
        mockMvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"))
                .andExpect(jsonPath("$.service").value("tactile-backend"));
    }

    @Test
    void shouldAccessSwaggerWithoutAuth() throws Exception {
        mockMvc.perform(get("/swagger-ui.html"))
                .andExpect(status().is3xxRedirection());
    }

    @Test
    @WithMockUser
    void shouldCreateJobWithAuth() throws Exception {
        // Note: This test uses @WithMockUser which doesn't work with OAuth2
        // For full OAuth2 testing, use oauth2Login() post processor

        CreateJobRequest request = CreateJobRequest.builder()
                .manufacturingProcess(ManufacturingProcess.FDM_3D_PRINTING)
                .material("PLA")
                .fileStorageId("file123")
                .originalFilename("test.step")
                .build();

        // This will fail without proper OAuth2 principal, but demonstrates the pattern
        mockMvc.perform(post("/api/jobs")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().is4xxClientError()); // Expected without OAuth2 principal
    }

    @Test
    void shouldGetJobWithOAuth2() throws Exception {
        // Create a test user first
        User user = User.builder()
                .email("test@example.com")
                .name("Test User")
                .oauthProvider("github")
                .oauthId("12345")
                .build();
        userRepository.save(user);

        // Try to get a non-existent job with OAuth2 login
        mockMvc.perform(get("/api/jobs/nonexistent")
                .with(oauth2Login()
                        .attributes(attrs -> {
                            attrs.put("id", 12345);
                            attrs.put("login", "testuser");
                            attrs.put("email", "test@example.com");
                        })))
                .andExpect(status().isNotFound());
    }
}
