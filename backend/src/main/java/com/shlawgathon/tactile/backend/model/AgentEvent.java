package com.shlawgathon.tactile.backend.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * Represents a single event in the agent's activity stream.
 * Events are displayed in real-time on the frontend like a chat sidebar.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "agent_events")
public class AgentEvent {

    @Id
    private String id;

    @Indexed
    private String jobId;

    private AgentEventType type;

    /**
     * Short title for display, e.g., "Analyzing overhang geometry"
     */
    private String title;

    /**
     * Detailed content - code, results, explanations, etc.
     */
    private String content;

    /**
     * Additional structured data for the event.
     */
    @Builder.Default
    private Map<String, Object> metadata = new HashMap<>();

    @CreatedDate
    private Instant createdAt;
}
