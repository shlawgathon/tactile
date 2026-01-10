package com.shlawgathon.tactile.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request to resume a failed job.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Request to resume a failed job")
public class ResumeJobRequest {

    @Schema(description = "Checkpoint ID to resume from (optional, uses latest if null)")
    private String checkpointId;
}
