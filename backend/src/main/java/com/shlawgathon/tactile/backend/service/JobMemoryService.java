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
     * Search for similar memories using vector similarity.
     * Note: Requires MongoDB Atlas vector search index to be configured.
     */
    public List<JobMemory> searchSimilar(String jobId, String query, int limit) {
        try {
            List<Double> queryEmbedding = voyageEmbeddingService.generateEmbedding(query);
            if (queryEmbedding == null || queryEmbedding.isEmpty()) {
                log.warn("Could not generate embedding for query, falling back to all memories");
                return getMemories(jobId).stream().limit(limit).collect(Collectors.toList());
            }

            // Use MongoDB Atlas Vector Search aggregation pipeline
            // Requires a vector search index named "memory_vector_index" on job_memories
            // collection
            org.bson.Document vectorSearchStage = new org.bson.Document("$vectorSearch",
                    new org.bson.Document()
                            .append("index", "memory_vector_index")
                            .append("path", "embedding")
                            .append("queryVector", queryEmbedding)
                            .append("numCandidates", limit * 10)
                            .append("limit", limit)
                            .append("filter", new org.bson.Document("jobId", jobId)));

            List<org.bson.Document> pipeline = List.of(vectorSearchStage);

            List<JobMemory> results = mongoTemplate.getCollection("job_memories")
                    .aggregate(pipeline, org.bson.Document.class)
                    .map(doc -> {
                        JobMemory memory = new JobMemory();
                        memory.setId(doc.getString("_id"));
                        memory.setJobId(doc.getString("jobId"));
                        memory.setContent(doc.getString("content"));
                        memory.setCategory(doc.getString("category"));
                        memory.setMetadata(doc.get("metadata", Map.class));
                        memory.setCreatedAt(doc.getDate("createdAt") != null
                                ? doc.getDate("createdAt").toInstant()
                                : null);
                        return memory;
                    })
                    .into(new java.util.ArrayList<>());

            log.info("Vector search found {} memories for job: {}", results.size(), jobId);

            if (results.isEmpty()) {
                log.warn("Vector search returned no results, falling back to all memories");
                return getMemories(jobId).stream().limit(limit).collect(Collectors.toList());
            }

            return results;

        } catch (Exception e) {
            log.error("Error performing vector search, falling back to all memories: {}", e.getMessage());
            return getMemories(jobId).stream().limit(limit).collect(Collectors.toList());
        }
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
