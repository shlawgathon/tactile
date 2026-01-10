package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.dto.MemoryResponse;
import com.shlawgathon.tactile.backend.dto.StoreMemoryRequest;
import com.shlawgathon.tactile.backend.model.AgentEventType;
import com.shlawgathon.tactile.backend.model.JobMemory;
import com.shlawgathon.tactile.backend.repository.JobMemoryRepository;
import com.shlawgathon.tactile.backend.websocket.JobWebSocketHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.aggregation.Aggregation;
import org.springframework.data.mongodb.core.aggregation.AggregationResults;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Service for managing job memories with vector embeddings.
 */
@Service
public class JobMemoryService {

    private static final Logger log = LoggerFactory.getLogger(JobMemoryService.class);

    private final JobMemoryRepository jobMemoryRepository;
    private final VoyageEmbeddingService voyageEmbeddingService;
    private final AgentEventService agentEventService;
    private final JobWebSocketHandler webSocketHandler;
    private final MongoTemplate mongoTemplate;

    public JobMemoryService(JobMemoryRepository jobMemoryRepository,
            VoyageEmbeddingService voyageEmbeddingService,
            AgentEventService agentEventService,
            JobWebSocketHandler webSocketHandler,
            MongoTemplate mongoTemplate) {
        this.jobMemoryRepository = jobMemoryRepository;
        this.voyageEmbeddingService = voyageEmbeddingService;
        this.agentEventService = agentEventService;
        this.webSocketHandler = webSocketHandler;
        this.mongoTemplate = mongoTemplate;
    }

    /**
     * Store a memory with auto-generated embedding.
     */
    public JobMemory storeMemory(String jobId, StoreMemoryRequest request) {
        return storeMemory(jobId, request.getContent(), request.getCategory(), request.getMetadata());
    }

    /**
     * Store a memory with auto-generated embedding.
     */
    public JobMemory storeMemory(String jobId, String content, String category,
            Map<String, Object> metadata) {
        List<Double> embedding = null;
        try {
            embedding = voyageEmbeddingService.generateEmbedding(content);
        } catch (Exception e) {
            log.warn("Failed to generate embedding for memory, storing without: {}", e.getMessage());
        }

        JobMemory memory = JobMemory.builder()
                .jobId(jobId)
                .content(content)
                .category(category)
                .metadata(metadata != null ? metadata : Map.of())
                .embedding(embedding)
                .build();

        memory = jobMemoryRepository.save(memory);
        log.debug("Stored memory: {} for job: {}", memory.getId(), jobId);

        // Create an event for the memory storage
        agentEventService.createEvent(jobId, AgentEventType.MEMORY_STORED,
                "Memory stored: " + (category != null ? category : "general"),
                content.length() > 100 ? content.substring(0, 100) + "..." : content,
                Map.of("memoryId", memory.getId()));

        // Broadcast memory stored event
        webSocketHandler.sendMemoryStored(jobId, memory);

        return memory;
    }

    /**
     * Get all memories for a job.
     */
    public List<JobMemory> getMemories(String jobId) {
        return jobMemoryRepository.findByJobId(jobId);
    }

    /**
     * Get memories by category.
     */
    public List<JobMemory> getMemoriesByCategory(String jobId, String category) {
        return jobMemoryRepository.findByJobIdAndCategory(jobId, category);
    }

    /**
     * Search for similar memories using cosine similarity.
     * Computes similarity in-memory without requiring a vector index.
     */
    public List<JobMemory> searchSimilar(String jobId, String query, int limit) {
        try {
            List<Double> queryEmbedding = voyageEmbeddingService.generateEmbedding(query);
            if (queryEmbedding == null || queryEmbedding.isEmpty()) {
                log.warn("Could not generate embedding for query, falling back to all memories");
                return getMemories(jobId).stream().limit(limit).collect(Collectors.toList());
            }

            // Get all memories for this job
            List<JobMemory> allMemories = getMemories(jobId);

            if (allMemories.isEmpty()) {
                return allMemories;
            }

            // Calculate cosine similarity for each memory and sort
            List<JobMemory> results = allMemories.stream()
                    .filter(m -> m.getEmbedding() != null && !m.getEmbedding().isEmpty())
                    .sorted((a, b) -> {
                        double simA = cosineSimilarity(queryEmbedding, a.getEmbedding());
                        double simB = cosineSimilarity(queryEmbedding, b.getEmbedding());
                        return Double.compare(simB, simA); // Descending order
                    })
                    .limit(limit)
                    .collect(Collectors.toList());

            log.info("Similarity search found {} memories for job: {}", results.size(), jobId);

            // If no memories have embeddings, fall back to returning all
            if (results.isEmpty()) {
                log.warn("No memories with embeddings found, returning all memories");
                return allMemories.stream().limit(limit).collect(Collectors.toList());
            }

            return results;

        } catch (Exception e) {
            log.error("Error performing similarity search: {}", e.getMessage());
            return getMemories(jobId).stream().limit(limit).collect(Collectors.toList());
        }
    }

    /**
     * Calculate cosine similarity between two vectors.
     */
    private double cosineSimilarity(List<Double> a, List<Double> b) {
        if (a.size() != b.size()) {
            return 0.0;
        }

        double dotProduct = 0.0;
        double normA = 0.0;
        double normB = 0.0;

        for (int i = 0; i < a.size(); i++) {
            dotProduct += a.get(i) * b.get(i);
            normA += a.get(i) * a.get(i);
            normB += b.get(i) * b.get(i);
        }

        if (normA == 0.0 || normB == 0.0) {
            return 0.0;
        }

        return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
    }

    /**
     * Convert memory to response DTO.
     */
    public MemoryResponse toResponse(JobMemory memory) {
        return MemoryResponse.builder()
                .id(memory.getId())
                .jobId(memory.getJobId())
                .content(memory.getContent())
                .category(memory.getCategory())
                .metadata(memory.getMetadata())
                .createdAt(memory.getCreatedAt())
                .build();
    }

    /**
     * Convert list of memories to response DTOs.
     */
    public List<MemoryResponse> toResponseList(List<JobMemory> memories) {
        return memories.stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
    }
}
