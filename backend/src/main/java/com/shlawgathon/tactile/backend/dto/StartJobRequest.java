package com.shlawgathon.tactile.backend.dto;

import com.shlawgathon.tactile.backend.model.ManufacturingProcess;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request to start a job on the Agent Module.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Request to start analysis on Agent Module")
public class StartJobRequest {

    @Schema(description = "Job ID")
    private String jobId;

    @Schema(description = "URL to download the STEP file")
    private String fileUrl;

    @Schema(description = "Manufacturing process for analysis")
    private ManufacturingProcess manufacturingProcess;

    @Schema(description = "Material type (optional)")
    private String material;

    @Schema(description = "Callback URL for status updates")
    private String callbackUrl;

    @Schema(description = "Checkpoint data to resume from (null for new job)")
    private ResumeCheckpoint resumeFromCheckpoint;
}
