package com.shlawgathon.tactile.backend.controller;

import com.shlawgathon.tactile.backend.dto.AgentEventRequest;
import com.shlawgathon.tactile.backend.dto.AgentEventResponse;
import com.shlawgathon.tactile.backend.model.AgentEvent;
import com.shlawgathon.tactile.backend.model.AgentEventType;
import com.shlawgathon.tactile.backend.service.AgentEventService;
import io.swagger.v3.oas.annotations.Hidden;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Internal controller for agent events.
 * Used by the Python agent module to submit activity events.
 */
@RestController
@RequestMapping("/internal/jobs/{jobId}/events")
@Tag(name = "Internal", description = "Internal callbacks from Agent Module")
@Hidden
public class AgentEventController {

    private final AgentEventService agentEventService;

    public AgentEventController(AgentEventService agentEventService) {
        this.agentEventService = agentEventService;
    }

    @PostMapping
    @Operation(summary = "Submit agent event", description = "Submit an agent event that will be broadcast to WebSocket clients")
    public ResponseEntity<AgentEventResponse> submitEvent(
            @PathVariable String jobId,
            @RequestBody AgentEventRequest request) {

        if (request.getType() == null) {
            return ResponseEntity.badRequest().build();
        }

        AgentEvent event = agentEventService.createEvent(jobId, request);
        return ResponseEntity.ok(agentEventService.toResponse(event));
    }

    @GetMapping
    @Operation(summary = "Get all events", description = "Get all events for a job in chronological order")
    public ResponseEntity<List<AgentEventResponse>> getEvents(
            @PathVariable String jobId,
            @RequestParam(required = false) AgentEventType type) {

        List<AgentEvent> events;
        if (type != null) {
            events = agentEventService.getEventsByJobIdAndType(jobId, type);
        } else {
            events = agentEventService.getEventsByJobId(jobId);
        }

        return ResponseEntity.ok(agentEventService.toResponseList(events));
    }
}
