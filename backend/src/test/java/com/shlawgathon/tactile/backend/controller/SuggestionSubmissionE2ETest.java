package com.shlawgathon.tactile.backend.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.shlawgathon.tactile.backend.BaseE2ETest;
import com.shlawgathon.tactile.backend.dto.SubmitSuggestionRequest;
import com.shlawgathon.tactile.backend.model.Job;
import com.shlawgathon.tactile.backend.model.JobStatus;
import com.shlawgathon.tactile.backend.model.ManufacturingProcess;
import com.shlawgathon.tactile.backend.repository.AnalysisResultRepository;
import com.shlawgathon.tactile.backend.repository.JobRepository;
import com.shlawgathon.tactile.backend.service.AgentCommunicationService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@AutoConfigureMockMvc
class SuggestionSubmissionE2ETest extends BaseE2ETest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private AnalysisResultRepository analysisResultRepository;

    @Autowired
    private JobRepository jobRepository;

    @MockBean
    private AgentCommunicationService agentCommunicationService;

    private String testJobId;

    @BeforeEach
    void setUp() {
        jobRepository.deleteAll();
        analysisResultRepository.deleteAll();

        // Create a test job
        Job job = Job.builder()
                .userId("test-user")
                .status(JobStatus.ANALYZING)
                .originalFilename("test.step")
                .fileStorageId("file123")
                .manufacturingProcess(ManufacturingProcess.FDM_3D_PRINTING)
                .material("PLA")
                .currentStage("ANALYZING")
                .build();
        job = jobRepository.save(job);
        testJobId = job.getId();
    }

    @Test
    void shouldSubmitSuggestion() throws Exception {
        SubmitSuggestionRequest request = SubmitSuggestionRequest.builder()
                .issueId("issue-1")
                .description("Add fillet to sharp edge")
                .expectedImprovement("Reduce stress concentration")
                .priority(1)
                .codeSnippet("result.edges().fillet(2.0)")
                .build();

        mockMvc.perform(post("/internal/jobs/" + testJobId + "/suggestions")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk());

        // Verify suggestion was added
        var result = analysisResultRepository.findByJobId(testJobId);
        assertThat(result).isPresent();
        assertThat(result.get().getSuggestions()).hasSize(1);
        assertThat(result.get().getSuggestions().get(0).getDescription())
                .isEqualTo("Add fillet to sharp edge");
    }

    @Test
    void shouldAppendMultipleSuggestions() throws Exception {
        // Submit first suggestion
        mockMvc.perform(post("/internal/jobs/" + testJobId + "/suggestions")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(
                        SubmitSuggestionRequest.builder()
                                .issueId("issue-1")
                                .description("First suggestion")
                                .priority(1)
                                .build())))
                .andExpect(status().isOk());

        // Submit second suggestion
        mockMvc.perform(post("/internal/jobs/" + testJobId + "/suggestions")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(
                        SubmitSuggestionRequest.builder()
                                .issueId("issue-2")
                                .description("Second suggestion")
                                .priority(2)
                                .build())))
                .andExpect(status().isOk());

        // Verify both suggestions were added
        var result = analysisResultRepository.findByJobId(testJobId);
        assertThat(result).isPresent();
        assertThat(result.get().getSuggestions()).hasSize(2);
    }

    @Test
    void shouldCreateAnalysisResultIfNotExists() throws Exception {
        // Create a new job without any existing AnalysisResult
        Job newJob = Job.builder()
                .userId("test-user")
                .status(JobStatus.ANALYZING)
                .originalFilename("new.step")
                .fileStorageId("file456")
                .manufacturingProcess(ManufacturingProcess.CNC_MACHINING)
                .currentStage("ANALYZING")
                .build();
        newJob = jobRepository.save(newJob);

        SubmitSuggestionRequest request = SubmitSuggestionRequest.builder()
                .issueId("issue-new")
                .description("New suggestion for new job")
                .priority(1)
                .build();

        mockMvc.perform(post("/internal/jobs/" + newJob.getId() + "/suggestions")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk());

        // Verify AnalysisResult was created
        var result = analysisResultRepository.findByJobId(newJob.getId());
        assertThat(result).isPresent();
        assertThat(result.get().getSuggestions()).hasSize(1);
    }

    @Test
    void shouldIncludePriorityInSuggestion() throws Exception {
        SubmitSuggestionRequest request = SubmitSuggestionRequest.builder()
                .issueId("issue-priority")
                .description("High priority fix")
                .priority(1)
                .build();

        mockMvc.perform(post("/internal/jobs/" + testJobId + "/suggestions")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk());

        var result = analysisResultRepository.findByJobId(testJobId);
        assertThat(result).isPresent();
        assertThat(result.get().getSuggestions().get(0).getPriority()).isEqualTo(1);
    }

    @Test
    void shouldIncludeCodeSnippet() throws Exception {
        String codeSnippet = "result = cq.Workplane().box(10, 10, 10).edges().fillet(1)";

        SubmitSuggestionRequest request = SubmitSuggestionRequest.builder()
                .issueId("issue-code")
                .description("Add fillet")
                .priority(2)
                .codeSnippet(codeSnippet)
                .build();

        mockMvc.perform(post("/internal/jobs/" + testJobId + "/suggestions")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk());

        var result = analysisResultRepository.findByJobId(testJobId);
        assertThat(result).isPresent();
        assertThat(result.get().getSuggestions().get(0).getCodeSnippet())
                .isEqualTo(codeSnippet);
    }
}
