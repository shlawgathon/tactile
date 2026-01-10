package com.shlawgathon.tactile.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * Checkpoint data from Agent Module.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Checkpoint data for job state persistence")
public class CheckpointRequest {

    @Schema(description = "Current stage name", example = "ANALYZE")
    private String stage;

    @Schema(description = "Stage index (0-based)", example = "2")
    private int stageIndex;

    @Schema(description = "Serialized agent state")
    private Map<String, Object> state;

    @Schema(description = "Reasoning trace from agent")
    private List<String> reasoningTrace;

    @Schema(description = "Intermediate results")
    private Map<String, Object> intermediateResults;

    @Schema(description = "Whether this checkpoint can be used for recovery")
    private boolean recoverable;
}
