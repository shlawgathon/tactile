package com.shlawgathon.tactile.backend.dto;

import com.shlawgathon.tactile.backend.model.AgentEventType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.Map;

/**
 * Response DTO for agent events.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AgentEventResponse {

    private String id;
    private String jobId;
    private AgentEventType type;
    private String title;
    private String content;
    private Map<String, Object> metadata;
    private Instant createdAt;
}
