package com.shlawgathon.tactile.backend.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.shlawgathon.tactile.backend.model.AgentEvent;
import com.shlawgathon.tactile.backend.model.Job;
import com.shlawgathon.tactile.backend.model.JobMemory;
import com.shlawgathon.tactile.backend.model.Suggestion;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class JobWebSocketHandler extends TextWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(JobWebSocketHandler.class);

    private final ObjectMapper objectMapper;

    // Map of jobId -> Map of sessionId -> session
    private final Map<String, Map<String, WebSocketSession>> jobSessions = new ConcurrentHashMap<>();

    public JobWebSocketHandler(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        String jobId = extractJobId(session);
        if (jobId != null) {
            jobSessions.computeIfAbsent(jobId, k -> new ConcurrentHashMap<>())
                    .put(session.getId(), session);
            log.info("WebSocket connected for job: {} session: {}", jobId, session.getId());
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        String jobId = extractJobId(session);
        if (jobId != null) {
            var sessions = jobSessions.get(jobId);
            if (sessions != null) {
                sessions.remove(session.getId());
                if (sessions.isEmpty()) {
                    jobSessions.remove(jobId);
                }
            }
            log.info("WebSocket disconnected for job: {} session: {}", jobId, session.getId());
        }
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        // Handle ping/pong or subscribe messages if needed
        log.debug("Received message: {}", message.getPayload());
    }

    /**
     * Send job update to all connected clients for a job.
     */
    public void sendJobUpdate(String jobId, Job job) {
        var sessions = jobSessions.get(jobId);
        if (sessions == null || sessions.isEmpty()) {
            return;
        }

        try {
            WebSocketMessage message = WebSocketMessage.builder()
                    .type("JOB_UPDATE")
                    .jobId(jobId)
                    .data(Map.of(
                            "status", job.getStatus().name(),
                            "currentStage", job.getCurrentStage() != null ? job.getCurrentStage() : "",
                            "progressPercent", job.getProgressPercent(),
                            "errorMessage", job.getErrorMessage() != null ? job.getErrorMessage() : ""))
                    .build();

            broadcastMessage(jobId, message);
        } catch (Exception e) {
            log.error("Failed to serialize job update for job: {}", jobId, e);
        }
    }

    /**
     * Send completion notification.
     */
    public void sendJobCompleted(String jobId, Job job) {
        var sessions = jobSessions.get(jobId);
        if (sessions == null || sessions.isEmpty()) {
            return;
        }

        try {
            WebSocketMessage message = WebSocketMessage.builder()
                    .type("JOB_COMPLETED")
                    .jobId(jobId)
                    .data(Map.of(
                            "totalIssues", job.getTotalIssues() != null ? job.getTotalIssues() : 0,
                            "criticalIssues", job.getCriticalIssues() != null ? job.getCriticalIssues() : 0,
                            "warnings", job.getWarnings() != null ? job.getWarnings() : 0))
                    .build();

            broadcastMessage(jobId, message);
        } catch (Exception e) {
            log.error("Failed to serialize completion message for job: {}", jobId, e);
        }
    }

    /**
     * Send agent event to all connected clients.
     */
    public void sendAgentEvent(String jobId, AgentEvent event) {
        var sessions = jobSessions.get(jobId);
        if (sessions == null || sessions.isEmpty()) {
            return;
        }

        try {
            WebSocketMessage message = WebSocketMessage.builder()
                    .type("AGENT_EVENT")
                    .jobId(jobId)
                    .data(Map.of(
                            "eventId", event.getId(),
                            "eventType", event.getType().name(),
                            "title", event.getTitle() != null ? event.getTitle() : "",
                            "content", event.getContent() != null ? event.getContent() : "",
                            "metadata", event.getMetadata() != null ? event.getMetadata() : Map.of(),
                            "createdAt", event.getCreatedAt() != null ? event.getCreatedAt().toString() : ""))
                    .build();

            broadcastMessage(jobId, message);
        } catch (Exception e) {
            log.error("Failed to serialize agent event for job: {}", jobId, e);
        }
    }

    /**
     * Send suggestion added notification.
     */
    public void sendSuggestionAdded(String jobId, Suggestion suggestion) {
        var sessions = jobSessions.get(jobId);
        if (sessions == null || sessions.isEmpty()) {
            return;
        }

        try {
            WebSocketMessage message = WebSocketMessage.builder()
                    .type("SUGGESTION_ADDED")
                    .jobId(jobId)
                    .data(Map.of(
                            "issueId", suggestion.getIssueId() != null ? suggestion.getIssueId() : "",
                            "description", suggestion.getDescription() != null ? suggestion.getDescription() : "",
                            "priority", suggestion.getPriority(),
                            "validated", suggestion.isValidated()))
                    .build();

            broadcastMessage(jobId, message);
        } catch (Exception e) {
            log.error("Failed to serialize suggestion for job: {}", jobId, e);
        }
    }

    /**
     * Send memory stored notification.
     */
    public void sendMemoryStored(String jobId, JobMemory memory) {
        var sessions = jobSessions.get(jobId);
        if (sessions == null || sessions.isEmpty()) {
            return;
        }

        try {
            WebSocketMessage message = WebSocketMessage.builder()
                    .type("MEMORY_STORED")
                    .jobId(jobId)
                    .data(Map.of(
                            "memoryId", memory.getId(),
                            "category", memory.getCategory() != null ? memory.getCategory() : "",
                            "contentPreview", memory.getContent() != null
                                    ? memory.getContent().substring(0, Math.min(100, memory.getContent().length()))
                                    : ""))
                    .build();

            broadcastMessage(jobId, message);
        } catch (Exception e) {
            log.error("Failed to serialize memory stored for job: {}", jobId, e);
        }
    }

    /**
     * Broadcast a message to all sessions for a job.
     */
    private void broadcastMessage(String jobId, WebSocketMessage message) {
        var sessions = jobSessions.get(jobId);
        if (sessions == null || sessions.isEmpty()) {
            return;
        }

        try {
            String jsonMessage = objectMapper.writeValueAsString(message);
            TextMessage textMessage = new TextMessage(jsonMessage);

            sessions.values().forEach(session -> {
                try {
                    if (session.isOpen()) {
                        session.sendMessage(textMessage);
                    }
                } catch (IOException e) {
                    log.error("Failed to send WebSocket message to session: {}", session.getId(), e);
                }
            });
        } catch (Exception e) {
            log.error("Failed to broadcast message for job: {}", jobId, e);
        }
    }

    private String extractJobId(WebSocketSession session) {
        String path = session.getUri().getPath();
        // Path format: /ws/jobs/{jobId}
        String[] parts = path.split("/");
        if (parts.length >= 4 && "jobs".equals(parts[2])) {
            return parts[3];
        }
        return null;
    }
}
