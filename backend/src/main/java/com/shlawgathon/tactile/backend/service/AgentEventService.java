package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.dto.AgentEventRequest;
import com.shlawgathon.tactile.backend.dto.AgentEventResponse;
import com.shlawgathon.tactile.backend.model.AgentEvent;
import com.shlawgathon.tactile.backend.model.AgentEventType;
import com.shlawgathon.tactile.backend.repository.AgentEventRepository;
import com.shlawgathon.tactile.backend.websocket.JobWebSocketHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Service for managing agent events and broadcasting to WebSocket clients.
 */
@Service
public class AgentEventService {

    private static final Logger log = LoggerFactory.getLogger(AgentEventService.class);

    private final AgentEventRepository agentEventRepository;
    private final JobWebSocketHandler webSocketHandler;

    public AgentEventService(AgentEventRepository agentEventRepository,
            JobWebSocketHandler webSocketHandler) {
        this.agentEventRepository = agentEventRepository;
        this.webSocketHandler = webSocketHandler;
    }

    /**
     * Create and broadcast an agent event.
     */
    public AgentEvent createEvent(String jobId, AgentEventRequest request) {
        return createEvent(jobId, request.getType(), request.getTitle(),
                request.getContent(), request.getMetadata());
    }

    /**
     * Create and broadcast an agent event.
     */
    public AgentEvent createEvent(String jobId, AgentEventType type, String title,
            String content, Map<String, Object> metadata) {
        AgentEvent event = AgentEvent.builder()
                .jobId(jobId)
                .type(type)
                .title(title)
                .content(content)
                .metadata(metadata != null ? metadata : Map.of())
                .build();

        event = agentEventRepository.save(event);
        log.debug("Created agent event: {} for job: {}", event.getId(), jobId);

        // Broadcast to WebSocket clients
        webSocketHandler.sendAgentEvent(jobId, event);

        return event;
    }

    /**
     * Get all events for a job in chronological order.
     */
    public List<AgentEvent> getEventsByJobId(String jobId) {
        return agentEventRepository.findByJobIdOrderByCreatedAtAsc(jobId);
    }

    /**
     * Get events filtered by type.
     */
    public List<AgentEvent> getEventsByJobIdAndType(String jobId, AgentEventType type) {
        return agentEventRepository.findByJobIdAndTypeOrderByCreatedAtAsc(jobId, type);
    }

    /**
     * Convert event to response DTO.
     */
    public AgentEventResponse toResponse(AgentEvent event) {
        return AgentEventResponse.builder()
                .id(event.getId())
                .jobId(event.getJobId())
                .type(event.getType())
                .title(event.getTitle())
                .content(event.getContent())
                .metadata(event.getMetadata())
                .createdAt(event.getCreatedAt())
                .build();
    }

    /**
     * Convert list of events to response DTOs.
     */
    public List<AgentEventResponse> toResponseList(List<AgentEvent> events) {
        return events.stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
    }
}
