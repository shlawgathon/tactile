package com.shlawgathon.tactile.backend.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request DTO for querying job memory (RAG-based chat).
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QueryMemoryRequest {

    private String query;
}
