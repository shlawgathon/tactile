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
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Checkpoint document for job state persistence and recovery.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "checkpoints")
public class Checkpoint {

    @Id
    private String id;

    @Indexed
    private String jobId;

    private String stage;
    private int stageIndex;

    // Serialized agent state
    private Map<String, Object> state;

    @Builder.Default
    private List<String> reasoningTrace = new ArrayList<>();

    private Map<String, Object> intermediateResults;

    @CreatedDate
    private Instant createdAt;

    @Builder.Default
    private boolean recoverable = true;
}
