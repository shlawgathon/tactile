package com.shlawgathon.tactile.backend.pubsub;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.shlawgathon.tactile.backend.config.RedisMessageConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * Publishes job events to Redis Pub/Sub for distribution across all backend
 * pods.
 */
@Component
public class JobEventPublisher {

    private static final Logger log = LoggerFactory.getLogger(JobEventPublisher.class);

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    public JobEventPublisher(StringRedisTemplate redisTemplate, ObjectMapper objectMapper) {
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }

    /**
     * Publish an event to the job events channel.
     *
     * @param jobId     The job ID
     * @param eventType The event type (AGENT_EVENT, JOB_UPDATE, etc.)
     * @param payload   The event payload data
     */
    public void publishEvent(String jobId, String eventType, Map<String, Object> payload) {
        try {
            JobEventMessage message = new JobEventMessage(jobId, eventType, payload);
            String json = objectMapper.writeValueAsString(message);

            redisTemplate.convertAndSend(RedisMessageConfig.JOB_EVENTS_CHANNEL, json);
            log.debug("[PUB/SUB] Published {} event for job: {}", eventType, jobId);
        } catch (Exception e) {
            log.error("[PUB/SUB] Failed to publish event for job: {}", jobId, e);
        }
    }

    /**
     * Message wrapper for Redis Pub/Sub.
     */
    public record JobEventMessage(String jobId, String eventType, Map<String, Object> payload) {
    }
}
