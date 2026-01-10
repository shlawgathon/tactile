package com.shlawgathon.tactile.backend.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.shlawgathon.tactile.backend.model.Job;
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

            String jsonMessage = objectMapper.writeValueAsString(message);
            TextMessage textMessage = new TextMessage(jsonMessage);

            sessions.values().forEach(session -> {
                try {
                    if (session.isOpen()) {
                        session.sendMessage(textMessage);
                    }
                } catch (IOException e) {
                    log.error("Failed to send completion message to session: {}", session.getId(), e);
                }
            });
        } catch (Exception e) {
            log.error("Failed to serialize completion message for job: {}", jobId, e);
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
