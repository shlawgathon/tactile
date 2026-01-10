package com.shlawgathon.tactile.backend.controller;

import com.shlawgathon.tactile.backend.dto.CreateJobRequest;
import com.shlawgathon.tactile.backend.dto.JobResponse;
import com.shlawgathon.tactile.backend.dto.ResumeJobRequest;
import com.shlawgathon.tactile.backend.model.AnalysisResult;
import com.shlawgathon.tactile.backend.model.Job;
import com.shlawgathon.tactile.backend.service.AnalysisResultService;
import com.shlawgathon.tactile.backend.service.JobService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/jobs")
@Tag(name = "Jobs", description = "CAD Analysis Job Management")
public class JobController {

    private final JobService jobService;
    private final AnalysisResultService analysisResultService;

    public JobController(JobService jobService, AnalysisResultService analysisResultService) {
        this.jobService = jobService;
        this.analysisResultService = analysisResultService;
    }

    @PostMapping
    @Operation(summary = "Create analysis job", description = "Create a new CAD analysis job")
    @ApiResponses({
            @ApiResponse(responseCode = "201", description = "Job created successfully"),
            @ApiResponse(responseCode = "400", description = "Invalid request"),
            @ApiResponse(responseCode = "401", description = "Unauthorized")
    })
    public ResponseEntity<JobResponse> createJob(
            @AuthenticationPrincipal OAuth2User principal,
            @Valid @RequestBody CreateJobRequest request) {

        String userId = principal.getAttribute("id").toString();
        Job job = jobService.createJob(userId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(toJobResponse(job));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get job status", description = "Get the current status and details of a job")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Job found"),
            @ApiResponse(responseCode = "404", description = "Job not found")
    })
    public ResponseEntity<JobResponse> getJob(
            @Parameter(description = "Job ID") @PathVariable String id) {

        return jobService.findById(id)
                .map(job -> ResponseEntity.ok(toJobResponse(job)))
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping
    @Operation(summary = "List user's jobs", description = "Get paginated list of jobs for the authenticated user")
    public ResponseEntity<Page<JobResponse>> listJobs(
            @AuthenticationPrincipal OAuth2User principal,
            Pageable pageable) {

        String userId = principal.getAttribute("id").toString();
        Page<JobResponse> jobs = jobService.findByUserId(userId, pageable)
                .map(this::toJobResponse);
        return ResponseEntity.ok(jobs);
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Cancel job", description = "Cancel a running job")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Job cancelled"),
            @ApiResponse(responseCode = "400", description = "Cannot cancel job in current state"),
            @ApiResponse(responseCode = "404", description = "Job not found")
    })
    public ResponseEntity<JobResponse> cancelJob(
            @Parameter(description = "Job ID") @PathVariable String id) {

        try {
            Job job = jobService.cancelJob(id);
            return ResponseEntity.ok(toJobResponse(job));
        } catch (IllegalStateException e) {
            return ResponseEntity.badRequest().build();
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
        }
    }

    @GetMapping("/{id}/results")
    @Operation(summary = "Get analysis results", description = "Get the analysis results for a completed job")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Results found"),
            @ApiResponse(responseCode = "404", description = "Results not found")
    })
    public ResponseEntity<AnalysisResult> getResults(
            @Parameter(description = "Job ID") @PathVariable String id) {

        return analysisResultService.findByJobId(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/resume")
    @Operation(summary = "Resume failed job", description = "Resume a failed job from the last checkpoint")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Job resumed"),
            @ApiResponse(responseCode = "400", description = "Cannot resume job in current state"),
            @ApiResponse(responseCode = "404", description = "Job not found")
    })
    public ResponseEntity<JobResponse> resumeJob(
            @Parameter(description = "Job ID") @PathVariable String id,
            @RequestBody(required = false) ResumeJobRequest request) {

        try {
            String checkpointId = request != null ? request.getCheckpointId() : null;
            Job job = jobService.resumeJob(id, checkpointId);
            return ResponseEntity.ok(toJobResponse(job));
        } catch (IllegalStateException e) {
            return ResponseEntity.badRequest().build();
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
        }
    }

    private JobResponse toJobResponse(Job job) {
        return JobResponse.builder()
                .id(job.getId())
                .userId(job.getUserId())
                .status(job.getStatus())
                .originalFilename(job.getOriginalFilename())
                .fileStorageId(job.getFileStorageId())
                .manufacturingProcess(job.getManufacturingProcess())
                .material(job.getMaterial())
                .currentStage(job.getCurrentStage())
                .progressPercent(job.getProgressPercent())
                .stagesCompleted(job.getStagesCompleted())
                .createdAt(job.getCreatedAt())
                .startedAt(job.getStartedAt())
                .completedAt(job.getCompletedAt())
                .errorMessage(job.getErrorMessage())
                .retryCount(job.getRetryCount())
                .totalIssues(job.getTotalIssues())
                .criticalIssues(job.getCriticalIssues())
                .warnings(job.getWarnings())
                .build();
    }
}
