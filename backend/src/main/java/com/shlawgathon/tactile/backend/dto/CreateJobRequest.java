package com.shlawgathon.tactile.backend.dto;

import com.shlawgathon.tactile.backend.model.JobStatus;
import com.shlawgathon.tactile.backend.model.ManufacturingProcess;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

/**
 * Request to create a new analysis job.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Request to create a new CAD analysis job")
public class CreateJobRequest {

    @NotNull
    @Schema(description = "Manufacturing process to analyze for", example = "FDM_3D_PRINTING")
    private ManufacturingProcess manufacturingProcess;

    @Schema(description = "Material type (optional)", example = "ABS")
    private String material;

    @Schema(description = "File storage ID from upload", example = "65a1b2c3d4e5f6g7h8i9j0k1")
    private String fileStorageId;

    @Schema(description = "Original filename", example = "bracket.step")
    private String originalFilename;
}

/**
 * Simplified job status response.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Job status response")
class JobStatusResponse {

    @Schema(description = "Job ID")
    private String id;

    @Schema(description = "Current status")
    private JobStatus status;

    @Schema(description = "Current stage")
    private String currentStage;

    @Schema(description = "Progress percentage")
    private int progressPercent;

    @Schema(description = "Error message if failed")
    private String errorMessage;
}
