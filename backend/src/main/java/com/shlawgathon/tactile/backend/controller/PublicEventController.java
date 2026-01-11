package com.shlawgathon.tactile.backend.controller;

import com.shlawgathon.tactile.backend.dto.AgentEventResponse;
import com.shlawgathon.tactile.backend.model.AgentEvent;
import com.shlawgathon.tactile.backend.model.AgentEventType;
import com.shlawgathon.tactile.backend.model.Job;
import com.shlawgathon.tactile.backend.service.AgentEventService;
import com.shlawgathon.tactile.backend.service.JobService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

/**
 * Public controller for accessing job events.
 * Secured by OAuth2 - requires authenticated user session.
 */
@RestController
@RequestMapping("/api/jobs/{jobId}/events")
@Tag(name = "Events", description = "Public event endpoints for job monitoring")
public class PublicEventController {

    private static final org.slf4j.Logger log = org.slf4j.LoggerFactory.getLogger(PublicEventController.class);

    private final AgentEventService agentEventService;
    private final JobService jobService;

    public PublicEventController(AgentEventService agentEventService, JobService jobService) {
        this.agentEventService = agentEventService;
        this.jobService = jobService;
    }

    @GetMapping
    @Operation(summary = "Get job events", description = "Get all events for a job in chronological order")
    public ResponseEntity<List<AgentEventResponse>> getEvents(
            @PathVariable String jobId,
            @RequestParam(required = false) AgentEventType type,
            @AuthenticationPrincipal(errorOnInvalidType = false) OAuth2User principal) {

        log.debug("Fetching events for job: {}", jobId);

        // Verify the job exists
        Optional<Job> jobOpt = jobService.findById(jobId);
        if (jobOpt.isEmpty()) {
            log.warn("Job not found: {}", jobId);
            return ResponseEntity.notFound().build();
        }

        // If user is authenticated, verify ownership
        if (principal != null) {
            // GitHub OAuth provides 'id' attribute (numeric) as the user ID
            Object idObj = principal.getAttribute("id");
            String userId = idObj != null ? idObj.toString() : principal.getName();

            Job job = jobOpt.get();
            if (!job.getUserId().equals(userId)) {
                log.warn("User {} (id: {}) attempted to access events for job {} owned by {}",
                    principal.getName(), userId, jobId, job.getUserId());
                return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
            }
        }

        // Fetch events
        List<AgentEvent> events;
        if (type != null) {
            events = agentEventService.getEventsByJobIdAndType(jobId, type);
        } else {
            events = agentEventService.getEventsByJobId(jobId);
        }

        return ResponseEntity.ok(agentEventService.toResponseList(events));
    }
}
