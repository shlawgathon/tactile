package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.BaseE2ETest;
import com.shlawgathon.tactile.backend.dto.CreateJobRequest;
import com.shlawgathon.tactile.backend.model.Job;
import com.shlawgathon.tactile.backend.model.JobStatus;
import com.shlawgathon.tactile.backend.model.ManufacturingProcess;
import com.shlawgathon.tactile.backend.repository.JobRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.MockBean;

import static org.junit.jupiter.api.Assertions.*;

class JobServiceE2ETest extends BaseE2ETest {

    @Autowired
    private JobService jobService;

    @Autowired
    private JobRepository jobRepository;

    @MockBean
    private AgentCommunicationService agentCommunicationService; // Mock external calls

    @BeforeEach
    void setUp() {
        jobRepository.deleteAll();
    }

    @Test
    void shouldCreateJob() {
        // Given
        CreateJobRequest request = CreateJobRequest.builder()
                .manufacturingProcess(ManufacturingProcess.FDM_3D_PRINTING)
                .material("PLA")
                .fileStorageId("file123")
                .originalFilename("bracket.step")
                .build();

        // When
        Job job = jobService.createJob("user123", request);

        // Then
        assertNotNull(job.getId());
        assertEquals(JobStatus.QUEUED, job.getStatus());
        assertEquals("bracket.step", job.getOriginalFilename());
        assertEquals(ManufacturingProcess.FDM_3D_PRINTING, job.getManufacturingProcess());
    }

    @Test
    void shouldFindJobsByUserId() {
        // Given
        CreateJobRequest request = CreateJobRequest.builder()
                .manufacturingProcess(ManufacturingProcess.CNC_MACHINING)
                .fileStorageId("file456")
                .originalFilename("part.step")
                .build();

        jobService.createJob("user456", request);
        jobService.createJob("user456", request);

        // When
        var jobs = jobService.findByUserId("user456");

        // Then
        assertEquals(2, jobs.size());
    }

    @Test
    void shouldUpdateJobStatus() {
        // Given
        CreateJobRequest request = CreateJobRequest.builder()
                .manufacturingProcess(ManufacturingProcess.INJECTION_MOLDING)
                .fileStorageId("file789")
                .originalFilename("mold.step")
                .build();
        Job job = jobService.createJob("user789", request);

        // When
        Job updatedJob = jobService.updateStatus(job.getId(), JobStatus.PARSING, "PARSE", 25);

        // Then
        assertEquals(JobStatus.PARSING, updatedJob.getStatus());
        assertEquals("PARSE", updatedJob.getCurrentStage());
        assertEquals(25, updatedJob.getProgressPercent());
        assertNotNull(updatedJob.getStartedAt());
    }

    @Test
    void shouldCompleteJob() {
        // Given
        CreateJobRequest request = CreateJobRequest.builder()
                .manufacturingProcess(ManufacturingProcess.FDM_3D_PRINTING)
                .fileStorageId("file101")
                .originalFilename("widget.step")
                .build();
        Job job = jobService.createJob("user101", request);

        // When
        Job completedJob = jobService.completeJob(job.getId(), 5, 2, 3);

        // Then
        assertEquals(JobStatus.COMPLETED, completedJob.getStatus());
        assertEquals(100, completedJob.getProgressPercent());
        assertEquals(5, completedJob.getTotalIssues());
        assertEquals(2, completedJob.getCriticalIssues());
        assertEquals(3, completedJob.getWarnings());
        assertNotNull(completedJob.getCompletedAt());
    }

    @Test
    void shouldFailJob() {
        // Given
        CreateJobRequest request = CreateJobRequest.builder()
                .manufacturingProcess(ManufacturingProcess.CNC_MACHINING)
                .fileStorageId("file202")
                .originalFilename("broken.step")
                .build();
        Job job = jobService.createJob("user202", request);

        // When
        Job failedJob = jobService.failJob(job.getId(), "Parse error: invalid geometry");

        // Then
        assertEquals(JobStatus.FAILED, failedJob.getStatus());
        assertEquals("Parse error: invalid geometry", failedJob.getErrorMessage());
        assertNotNull(failedJob.getCompletedAt());
    }

    @Test
    void shouldCancelJob() {
        // Given
        CreateJobRequest request = CreateJobRequest.builder()
                .manufacturingProcess(ManufacturingProcess.FDM_3D_PRINTING)
                .fileStorageId("file303")
                .originalFilename("cancel.step")
                .build();
        Job job = jobService.createJob("user303", request);

        // When
        Job cancelledJob = jobService.cancelJob(job.getId());

        // Then
        assertEquals(JobStatus.CANCELLED, cancelledJob.getStatus());
        assertNotNull(cancelledJob.getCompletedAt());
    }

    @Test
    void shouldNotCancelCompletedJob() {
        // Given
        CreateJobRequest request = CreateJobRequest.builder()
                .manufacturingProcess(ManufacturingProcess.INJECTION_MOLDING)
                .fileStorageId("file404")
                .originalFilename("done.step")
                .build();
        Job job = jobService.createJob("user404", request);
        jobService.completeJob(job.getId(), 0, 0, 0);

        // When/Then
        assertThrows(IllegalStateException.class, () -> jobService.cancelJob(job.getId()));
    }
}
