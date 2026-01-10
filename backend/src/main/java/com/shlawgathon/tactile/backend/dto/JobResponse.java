package com.shlawgathon.tactile.backend.dto;

import com.shlawgathon.tactile.backend.model.JobStatus;
import com.shlawgathon.tactile.backend.model.ManufacturingProcess;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

/**
 * Response containing job details.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Job details response")
public class JobResponse {

    @Schema(description = "Job ID")
    private String id;

    @Schema(description = "User ID who created the job")
    private String userId;

    @Schema(description = "Current job status")
    private JobStatus status;

    @Schema(description = "Original filename")
    private String originalFilename;

    @Schema(description = "File storage ID")
    private String fileStorageId;

    @Schema(description = "Manufacturing process")
    private ManufacturingProcess manufacturingProcess;

    @Schema(description = "Material type")
    private String material;

    @Schema(description = "Current processing stage")
    private String currentStage;

    @Schema(description = "Progress percentage (0-100)")
    private int progressPercent;

    @Schema(description = "List of completed stages")
    private List<String> stagesCompleted;

    @Schema(description = "Job creation timestamp")
    private Instant createdAt;

    @Schema(description = "Job start timestamp")
    private Instant startedAt;

    @Schema(description = "Job completion timestamp")
    private Instant completedAt;

    @Schema(description = "Error message if failed")
    private String errorMessage;

    @Schema(description = "Retry count")
    private int retryCount;

    @Schema(description = "Total issues found")
    private Integer totalIssues;

    @Schema(description = "Critical issues count")
    private Integer criticalIssues;

    @Schema(description = "Warnings count")
    private Integer warnings;
}
