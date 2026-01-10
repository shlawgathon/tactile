package com.shlawgathon.tactile.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Callback from Agent Module on job failure.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Job failure callback from Agent Module")
public class FailureCallback {

    @Schema(description = "Error message")
    private String errorMessage;

    @Schema(description = "Error type")
    private String errorType;

    @Schema(description = "Whether this failure is recoverable")
    private boolean recoverable;
}
