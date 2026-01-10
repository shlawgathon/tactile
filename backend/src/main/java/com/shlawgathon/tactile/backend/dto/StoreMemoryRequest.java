package com.shlawgathon.tactile.backend.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * Request DTO for storing a memory.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StoreMemoryRequest {

    private String content;

    /**
     * Category of the memory: geometry, issue, material, dimension, etc.
     */
    private String category;

    private Map<String, Object> metadata;
}
