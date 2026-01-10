package com.shlawgathon.tactile.backend.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.Map;

/**
 * Response DTO for job memories.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MemoryResponse {

    private String id;
    private String jobId;
    private String content;
    private String category;
    private Map<String, Object> metadata;
    private Instant createdAt;
}
