package com.shlawgathon.tactile.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * Checkpoint data for resuming a job.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Checkpoint data for job resume")
public class ResumeCheckpoint {

    @Schema(description = "Stage to resume from")
    private String stage;

    @Schema(description = "Saved state")
    private Map<String, Object> state;

    @Schema(description = "Intermediate results")
    private Map<String, Object> intermediateResults;
}
