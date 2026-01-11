package com.shlawgathon.tactile.backend.pubsub;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.shlawgathon.tactile.backend.websocket.JobWebSocketHandler;
import com.shlawgathon.tactile.backend.websocket.PublicJobWebSocketHandler;
import com.shlawgathon.tactile.backend.websocket.WebSocketMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * Subscribes to Redis Pub/Sub job events and dispatches to local WebSocket
 * sessions.
 * Each pod receives all events and broadcasts to its connected clients.
 */
@Component
public class JobEventSubscriber {

    private static final Logger log = LoggerFactory.getLogger(JobEventSubscriber.class);

    private final ObjectMapper objectMapper;
    private final JobWebSocketHandler jobWebSocketHandler;
    private final PublicJobWebSocketHandler publicJobWebSocketHandler;

    public JobEventSubscriber(
            ObjectMapper objectMapper,
            JobWebSocketHandler jobWebSocketHandler,
            PublicJobWebSocketHandler publicJobWebSocketHandler) {
        this.objectMapper = objectMapper;
        this.jobWebSocketHandler = jobWebSocketHandler;
        this.publicJobWebSocketHandler = publicJobWebSocketHandler;
    }

    /**
     * Handle incoming Redis Pub/Sub message.
     * Called by Spring's MessageListenerAdapter.
     */
    @SuppressWarnings("unchecked")
    public void handleMessage(String message) {
        try {
            var eventMessage = objectMapper.readValue(message, JobEventPublisher.JobEventMessage.class);
            String jobId = eventMessage.jobId();
            String eventType = eventMessage.eventType();
            Map<String, Object> payload = eventMessage.payload();

            log.debug("[PUB/SUB] Received {} event for job: {}", eventType, jobId);

            // Build WebSocket message
            WebSocketMessage wsMessage = WebSocketMessage.builder()
                    .type(eventType)
                    .jobId(jobId)
                    .data(payload)
                    .build();

            // Broadcast to all local WebSocket sessions
            broadcastToLocalSessions(jobId, wsMessage);

        } catch (Exception e) {
            log.error("[PUB/SUB] Failed to process message: {}", message, e);
        }
    }

    private void broadcastToLocalSessions(String jobId, WebSocketMessage message) {
        // Broadcast to internal handler (agent module connections)
        jobWebSocketHandler.broadcastFromPubSub(jobId, message);

        // Broadcast to public handler (frontend connections)
        publicJobWebSocketHandler.broadcastFromPubSub(jobId, message);
    }
}
