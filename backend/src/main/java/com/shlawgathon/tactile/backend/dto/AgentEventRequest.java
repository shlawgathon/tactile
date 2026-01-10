package com.shlawgathon.tactile.backend.dto;

import com.shlawgathon.tactile.backend.model.AgentEventType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * Request DTO for submitting an agent event.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AgentEventRequest {

    private AgentEventType type;
    private String title;
    private String content;
    private Map<String, Object> metadata;
}
