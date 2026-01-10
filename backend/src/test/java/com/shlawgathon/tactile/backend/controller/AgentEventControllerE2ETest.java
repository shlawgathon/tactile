package com.shlawgathon.tactile.backend.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.shlawgathon.tactile.backend.BaseE2ETest;
import com.shlawgathon.tactile.backend.dto.AgentEventRequest;
import com.shlawgathon.tactile.backend.model.AgentEventType;
import com.shlawgathon.tactile.backend.repository.AgentEventRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@AutoConfigureMockMvc
class AgentEventControllerE2ETest extends BaseE2ETest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private AgentEventRepository agentEventRepository;

    @BeforeEach
    void setUp() {
        agentEventRepository.deleteAll();
    }

    @Test
    void shouldSubmitAgentEvent() throws Exception {
        AgentEventRequest request = AgentEventRequest.builder()
                .type(AgentEventType.ANALYZING)
                .title("Analyzing overhang geometry")
                .content("Examining overhang angles greater than 45 degrees")
                .metadata(Map.of("feature", "overhang"))
                .build();

        mockMvc.perform(post("/internal/jobs/test-job-123/events")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.jobId").value("test-job-123"))
                .andExpect(jsonPath("$.type").value("ANALYZING"))
                .andExpect(jsonPath("$.title").value("Analyzing overhang geometry"));
    }

    @Test
    void shouldGetAllEventsForJob() throws Exception {
        // Create multiple events
        for (int i = 0; i < 3; i++) {
            AgentEventRequest request = AgentEventRequest.builder()
                    .type(AgentEventType.ANALYZING)
                    .title("Event " + i)
                    .content("Content " + i)
                    .build();

            mockMvc.perform(post("/internal/jobs/test-job-456/events")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isOk());
        }

        // Get all events
        mockMvc.perform(get("/internal/jobs/test-job-456/events"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3));
    }

    @Test
    void shouldRejectEventWithMissingType() throws Exception {
        AgentEventRequest request = AgentEventRequest.builder()
                .title("Missing type event")
                .content("This event has no type")
                .build();

        mockMvc.perform(post("/internal/jobs/test-job-789/events")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void shouldFilterEventsByType() throws Exception {
        // Create events of different types
        mockMvc.perform(post("/internal/jobs/test-job-filter/events")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(
                        AgentEventRequest.builder()
                                .type(AgentEventType.ANALYZING)
                                .title("Analyzing event")
                                .build())))
                .andExpect(status().isOk());

        mockMvc.perform(post("/internal/jobs/test-job-filter/events")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(
                        AgentEventRequest.builder()
                                .type(AgentEventType.RUNNING_CODE)
                                .title("Running code event")
                                .build())))
                .andExpect(status().isOk());

        // Filter by type
        mockMvc.perform(get("/internal/jobs/test-job-filter/events?type=ANALYZING"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].type").value("ANALYZING"));
    }

    @Test
    void shouldHandleNonExistentJob() throws Exception {
        mockMvc.perform(get("/internal/jobs/nonexistent/events"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(0));
    }
}
