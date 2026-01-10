package com.shlawgathon.tactile.backend.controller;

import com.shlawgathon.tactile.backend.dto.MemoryResponse;
import com.shlawgathon.tactile.backend.dto.QueryMemoryRequest;
import com.shlawgathon.tactile.backend.dto.QueryMemoryResponse;
import com.shlawgathon.tactile.backend.dto.StoreMemoryRequest;
import com.shlawgathon.tactile.backend.model.JobMemory;
import com.shlawgathon.tactile.backend.service.JobMemoryService;
import com.shlawgathon.tactile.backend.service.MemoryQueryService;
import io.swagger.v3.oas.annotations.Hidden;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Controller for job memory operations.
 * Internal endpoints for agent use, and public endpoint for RAG querying.
 */
@RestController
@Tag(name = "Memory", description = "Job memory management and querying")
public class MemoryController {

    private final JobMemoryService jobMemoryService;
    private final MemoryQueryService memoryQueryService;

    public MemoryController(JobMemoryService jobMemoryService,
            MemoryQueryService memoryQueryService) {
        this.jobMemoryService = jobMemoryService;
        this.memoryQueryService = memoryQueryService;
    }

    // ==================== Internal Endpoints (Agent Use) ====================

    @PostMapping("/internal/jobs/{jobId}/memory")
    @Operation(summary = "Store memory", description = "Store a memory for a job with auto-generated embedding")
    @Hidden
    public ResponseEntity<MemoryResponse> storeMemory(
            @PathVariable String jobId,
            @RequestBody StoreMemoryRequest request) {

        if (request.getContent() == null || request.getContent().isBlank()) {
            return ResponseEntity.badRequest().build();
        }

        JobMemory memory = jobMemoryService.storeMemory(jobId, request);
        return ResponseEntity.ok(jobMemoryService.toResponse(memory));
    }

    @GetMapping("/internal/jobs/{jobId}/memory")
    @Operation(summary = "Get all memories", description = "Get all memories for a job")
    @Hidden
    public ResponseEntity<List<MemoryResponse>> getMemories(
            @PathVariable String jobId,
            @RequestParam(required = false) String category) {

        List<JobMemory> memories;
        if (category != null && !category.isBlank()) {
            memories = jobMemoryService.getMemoriesByCategory(jobId, category);
        } else {
            memories = jobMemoryService.getMemories(jobId);
        }

        return ResponseEntity.ok(jobMemoryService.toResponseList(memories));
    }

    // ==================== Public Endpoint (Frontend Chat) ====================

    @PostMapping("/api/jobs/{jobId}/query")
    @Operation(summary = "Query job memory", description = "Query the job's knowledge base using RAG")
    public ResponseEntity<QueryMemoryResponse> queryMemory(
            @PathVariable String jobId,
            @RequestBody QueryMemoryRequest request) {

        if (request.getQuery() == null || request.getQuery().isBlank()) {
            return ResponseEntity.badRequest().build();
        }

        try {
            String answer = memoryQueryService.queryMemory(jobId, request.getQuery());
            int sourcesUsed = memoryQueryService.getSourcesCount(jobId, request.getQuery());

            return ResponseEntity.ok(QueryMemoryResponse.builder()
                    .answer(answer)
                    .sourcesUsed(sourcesUsed)
                    .build());
        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                    .body(QueryMemoryResponse.builder()
                            .answer("An error occurred while processing your query.")
                            .sourcesUsed(0)
                            .build());
        }
    }
}
