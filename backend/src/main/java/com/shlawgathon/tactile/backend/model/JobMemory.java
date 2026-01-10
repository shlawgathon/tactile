package com.shlawgathon.tactile.backend.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Stores important findings about a CAD file with vector embeddings for
 * semantic search.
 * Used for RAG-based querying of job knowledge.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "job_memories")
public class JobMemory {

    @Id
    private String id;

    @Indexed
    private String jobId;

    /**
     * The memory content text.
     */
    private String content;

    /**
     * Category of the memory: geometry, issue, material, dimension, etc.
     */
    private String category;

    /**
     * Additional structured metadata.
     */
    @Builder.Default
    private Map<String, Object> metadata = new HashMap<>();

    /**
     * Vector embedding for semantic search (1024-dim from Voyage AI voyage-3).
     */
    private List<Double> embedding;

    @CreatedDate
    private Instant createdAt;
}
