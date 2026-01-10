package com.shlawgathon.tactile.backend.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.shlawgathon.tactile.backend.model.AgentEvent;
import com.shlawgathon.tactile.backend.model.Job;
import com.shlawgathon.tactile.backend.model.Suggestion;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.security.Principal;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Public WebSocket handler for authenticated clients.
 * Validates user session on connection and broadcasts events to subscribed
 * clients.
 */
@Component
public class PublicJobWebSocketHandler extends TextWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(PublicJobWebSocketHandler.class);

    private final ObjectMapper objectMapper;

    // Map of jobId -> Map of sessionId -> session
    private final Map<String, Map<String, WebSocketSession>> jobSessions = new ConcurrentHashMap<>();

    public PublicJobWebSocketHandler(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        String jobId = extractJobId(session);
        Principal principal = session.getPrincipal();

        if (principal == null) {
            log.warn("WebSocket connection rejected - no authenticated user for job: {}", jobId);
            try {
                session.close(CloseStatus.POLICY_VIOLATION);
            } catch (IOException e) {
                log.error("Failed to close unauthenticated WebSocket session", e);
            }
            return;
        }

        if (jobId != null) {
            jobSessions.computeIfAbsent(jobId, k -> new ConcurrentHashMap<>())
                    .put(session.getId(), session);
            log.info("Public WebSocket connected for job: {} session: {} user: {}",
                    jobId, session.getId(), principal.getName());

            // Send a welcome message
            try {
                WebSocketMessage welcomeMessage = WebSocketMessage.builder()
                        .type("CONNECTED")
                        .jobId(jobId)
                        .data(Map.of("message", "Connected to job event stream"))
                        .build();
                session.sendMessage(new TextMessage(objectMapper.writeValueAsString(welcomeMessage)));
            } catch (IOException e) {
                log.error("Failed to send welcome message", e);
            }
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
            log.info("Public WebSocket disconnected for job: {} session: {}", jobId, session.getId());
        }
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        // Handle ping/pong or subscribe messages if needed
        log.debug("Received message from public client: {}", message.getPayload());
    }

    /**
     * Send agent event to all connected public clients for a job.
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
            log.error("Failed to send agent event to public clients for job: {}", jobId, e);
        }
    }

    /**
     * Send job update to all connected public clients for a job.
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
            log.error("Failed to send job update to public clients for job: {}", jobId, e);
        }
    }

    /**
     * Send suggestion added notification to all connected public clients.
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
            log.error("Failed to send suggestion to public clients for job: {}", jobId, e);
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
                    log.error("Failed to send WebSocket message to public session: {}", session.getId(), e);
                }
            });
        } catch (Exception e) {
            log.error("Failed to broadcast message to public clients for job: {}", jobId, e);
        }
    }

    private String extractJobId(WebSocketSession session) {
        String path = session.getUri().getPath();
        // Path format: /ws/public/jobs/{jobId}
        String[] parts = path.split("/");
        if (parts.length >= 5 && "public".equals(parts[2]) && "jobs".equals(parts[3])) {
            return parts[4];
        }
        return null;
    }
}
