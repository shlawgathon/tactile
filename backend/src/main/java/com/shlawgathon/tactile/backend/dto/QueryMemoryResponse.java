package com.shlawgathon.tactile.backend.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Response DTO for memory queries.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QueryMemoryResponse {

    private String answer;
    private int sourcesUsed;
}
