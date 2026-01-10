package com.shlawgathon.tactile.backend.controller;

import com.shlawgathon.tactile.backend.dto.AgentEventRequest;
import com.shlawgathon.tactile.backend.dto.CheckpointRequest;
import com.shlawgathon.tactile.backend.dto.CompletionCallback;
import com.shlawgathon.tactile.backend.dto.FailureCallback;
import com.shlawgathon.tactile.backend.dto.SubmitSuggestionRequest;
import com.shlawgathon.tactile.backend.model.*;
import com.shlawgathon.tactile.backend.service.*;
import com.shlawgathon.tactile.backend.websocket.JobWebSocketHandler;
import io.swagger.v3.oas.annotations.Hidden;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/internal/jobs/{jobId}")
@Tag(name = "Internal", description = "Internal callbacks from Agent Module")
@Hidden // Hide from public Swagger UI
public class InternalCallbackController {

    private static final org.slf4j.Logger log = org.slf4j.LoggerFactory.getLogger(InternalCallbackController.class);

    private final JobService jobService;
    private final CheckpointService checkpointService;
    private final AnalysisResultService analysisResultService;
    private final FileStorageService fileStorageService;
    private final JobWebSocketHandler webSocketHandler;
    private final ThesysService thesysService;
    private final AgentEventService agentEventService;

    public InternalCallbackController(JobService jobService,
            CheckpointService checkpointService,
            AnalysisResultService analysisResultService,
            FileStorageService fileStorageService,
            JobWebSocketHandler webSocketHandler,
            ThesysService thesysService,
            AgentEventService agentEventService) {
        this.jobService = jobService;
        this.checkpointService = checkpointService;
        this.analysisResultService = analysisResultService;
        this.fileStorageService = fileStorageService;
        this.webSocketHandler = webSocketHandler;
        this.thesysService = thesysService;
        this.agentEventService = agentEventService;
    }

    @PostMapping("/checkpoint")
    @Operation(summary = "Save checkpoint", description = "Save a checkpoint from agent module")
    public ResponseEntity<Void> saveCheckpoint(
            @PathVariable String jobId,
            @RequestBody CheckpointRequest request) {

        log.info("[AGENT CHECKPOINT] Job: {} | Stage: {} | Index: {}",
                jobId, request.getStage(), request.getStageIndex());

        // Save checkpoint
        Checkpoint checkpoint = checkpointService.saveCheckpoint(jobId, request);
        log.info("[AGENT CHECKPOINT] Job: {} | Saved checkpoint: {}", jobId, checkpoint.getId());

        // Update job status
        JobStatus status = mapStageToStatus(request.getStage());
        int progress = calculateProgress(request.getStageIndex());
        log.info("[AGENT CHECKPOINT] Job: {} | Status: {} | Progress: {}%", jobId, status, progress);

        jobService.updateStatus(jobId, status, request.getStage(), progress);
        jobService.completeStage(jobId, request.getStage());

        // Update last checkpoint reference
        jobService.findById(jobId).ifPresent(job -> {
            job.setLastCheckpointId(checkpoint.getId());
            // Note: This should be saved via repository directly
        });

        return ResponseEntity.ok().build();
    }

    @PostMapping("/complete")
    @Operation(summary = "Complete job", description = "Mark job as completed with results")
    public ResponseEntity<Void> completeJob(
            @PathVariable String jobId,
            @RequestBody CompletionCallback callback) {

        log.info("[AGENT COMPLETE] Job: {} | Success: {}", jobId, callback.isSuccess());

        if (callback.getResults() != null) {
            var results = callback.getResults();
            log.info("[AGENT COMPLETE] Job: {} | Issues: {} | Suggestions: {} | HasMarkdown: {}",
                    jobId,
                    results.getIssues() != null ? results.getIssues().size() : 0,
                    results.getSuggestions() != null ? results.getSuggestions().size() : 0,
                    results.getMarkdownReport() != null);
        }

        if (!callback.isSuccess()) {
            log.warn("[AGENT COMPLETE] Job: {} | Callback reported failure!", jobId);
            return ResponseEntity.badRequest().build();
        }

        // Store output files
        String modifiedStepId = null;
        if (callback.getOutputFiles() != null && callback.getOutputFiles().getModifiedStep() != null) {
            modifiedStepId = fileStorageService.uploadBase64(
                    callback.getOutputFiles().getModifiedStep(),
                    "modified.step",
                    "application/step");
        }

        List<String> previewImageIds = List.of();
        if (callback.getOutputFiles() != null && callback.getOutputFiles().getPreviewImages() != null) {
            previewImageIds = callback.getOutputFiles().getPreviewImages().stream()
                    .map(img -> fileStorageService.uploadBase64(img, "preview.png", "image/png"))
                    .collect(Collectors.toList());
        }

        // Build analysis result
        var results = callback.getResults();
        var geom = results.getGeometrySummary();
        String markdownReport = results.getMarkdownReport();

        AnalysisResult analysisResult = AnalysisResult.builder()
                .jobId(jobId)
                .boundingBox(geom != null ? toBoundingBox(geom.getBoundingBox()) : null)
                .volume(geom != null ? geom.getVolume() : null)
                .surfaceArea(geom != null ? geom.getSurfaceArea() : null)
                .faceCount(geom != null ? geom.getFaceCount() : null)
                .edgeCount(geom != null ? geom.getEdgeCount() : null)
                .issues(results.getIssues())
                .issuesBySeverity(countBySeverity(results.getIssues()))
                .suggestions(results.getSuggestions())
                .generatedCodeSnippets(results.getGeneratedCode())
                .modifiedStepFileId(modifiedStepId)
                .previewImageIds(previewImageIds)
                .markdownReport(markdownReport)
                .build();

        analysisResultService.save(analysisResult);

        // Count issues
        int totalIssues = results.getIssues() != null ? results.getIssues().size() : 0;
        int criticalIssues = results.getIssues() != null
                ? (int) results.getIssues().stream().filter(i -> i.getSeverity() == Severity.ERROR).count()
                : 0;
        int warnings = results.getIssues() != null
                ? (int) results.getIssues().stream().filter(i -> i.getSeverity() == Severity.WARNING).count()
                : 0;

        jobService.completeJob(jobId, totalIssues, criticalIssues, warnings);

        // Emit SUCCESS event
        AgentEventRequest successEvent = new AgentEventRequest();
        successEvent.setType(AgentEventType.SUCCESS);
        successEvent.setTitle("Analysis Complete");
        successEvent.setContent("DFM analysis completed with " + totalIssues + " issues found.");
        agentEventService.createEvent(jobId, successEvent);

        // Convert markdown to Thesys C1 UI format (async-ish, in background)
        if (markdownReport != null && !markdownReport.isBlank()) {
            try {
                String c1UiReport = thesysService.chatCompletion(List.of(
                        Map.of("role", "system", "content",
                                "Convert this DFM analysis markdown report into a visually rich UI. " +
                                        "Use cards, charts, and clear visual hierarchy."),
                        Map.of("role", "user", "content", markdownReport)));

                // Update the analysis result with C1 UI
                analysisResult.setC1UiReport(c1UiReport);
                analysisResultService.save(analysisResult);

                // Emit GENUI_GEN_SUCCESS event
                AgentEventRequest genuiEvent = new AgentEventRequest();
                genuiEvent.setType(AgentEventType.GENUI_GEN_SUCCESS);
                genuiEvent.setTitle("UI Generation Complete");
                genuiEvent.setContent("Thesys C1 UI report generated successfully.");
                agentEventService.createEvent(jobId, genuiEvent);
            } catch (Exception e) {
                log.error("Failed to generate C1 UI from markdown: {}", e.getMessage());
            }
        }

        return ResponseEntity.ok().build();
    }

    @PostMapping("/fail")
    @Operation(summary = "Fail job", description = "Mark job as failed")
    public ResponseEntity<Void> failJob(
            @PathVariable String jobId,
            @RequestBody FailureCallback callback) {

        jobService.failJob(jobId, callback.getErrorMessage());
        return ResponseEntity.ok().build();
    }

    @PostMapping("/suggestions")
    @Operation(summary = "Submit suggestion", description = "Submit a DFM suggestion incrementally")
    public ResponseEntity<Void> submitSuggestion(
            @PathVariable String jobId,
            @RequestBody SubmitSuggestionRequest request) {

        // Build suggestion
        Suggestion suggestion = Suggestion.builder()
                .issueId(request.getIssueId())
                .description(request.getDescription())
                .expectedImprovement(request.getExpectedImprovement())
                .priority(request.getPriority())
                .codeSnippet(request.getCodeSnippet())
                .validated(false)
                .build();

        // Add to analysis result (creates if not exists)
        analysisResultService.addSuggestion(jobId, suggestion);

        // Broadcast to WebSocket clients
        webSocketHandler.sendSuggestionAdded(jobId, suggestion);

        return ResponseEntity.ok().build();
    }

    private JobStatus mapStageToStatus(String stage) {
        return switch (stage.toUpperCase()) {
            case "PARSE" -> JobStatus.PARSING;
            case "ANALYZE" -> JobStatus.ANALYZING;
            case "SUGGEST" -> JobStatus.SUGGESTING;
            case "VALIDATE" -> JobStatus.VALIDATING;
            default -> JobStatus.QUEUED;
        };
    }

    private int calculateProgress(int stageIndex) {
        // 4 stages: PARSE, ANALYZE, SUGGEST, VALIDATE
        return Math.min(100, (stageIndex + 1) * 25);
    }

    private BoundingBox toBoundingBox(Map<String, Double> bbox) {
        if (bbox == null)
            return null;
        return BoundingBox.builder()
                .minX(bbox.getOrDefault("minX", 0.0))
                .minY(bbox.getOrDefault("minY", 0.0))
                .minZ(bbox.getOrDefault("minZ", 0.0))
                .maxX(bbox.getOrDefault("maxX", 0.0))
                .maxY(bbox.getOrDefault("maxY", 0.0))
                .maxZ(bbox.getOrDefault("maxZ", 0.0))
                .build();
    }

    private Map<String, Integer> countBySeverity(List<Issue> issues) {
        if (issues == null)
            return Map.of();
        return issues.stream()
                .collect(Collectors.groupingBy(
                        i -> i.getSeverity().name(),
                        Collectors.collectingAndThen(Collectors.counting(), Long::intValue)));
    }
}
