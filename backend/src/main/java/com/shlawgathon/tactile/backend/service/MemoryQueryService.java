package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.model.JobMemory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Service for RAG-based querying of job memories.
 * Uses vector search to find relevant memories and Fireworks AI to generate
 * responses.
 */
@Service
public class MemoryQueryService {

    private static final Logger log = LoggerFactory.getLogger(MemoryQueryService.class);

    private final JobMemoryService jobMemoryService;
    private final FireworksAIService fireworksAIService;

    private static final int MAX_CONTEXT_MEMORIES = 5;

    public MemoryQueryService(JobMemoryService jobMemoryService,
            FireworksAIService fireworksAIService) {
        this.jobMemoryService = jobMemoryService;
        this.fireworksAIService = fireworksAIService;
    }

    /**
     * Query the job's memory using RAG.
     *
     * @param jobId     The job ID to query
     * @param userQuery The user's question
     * @return Generated answer based on job memories
     */
    public String queryMemory(String jobId, String userQuery) throws Exception {
        // 1. Find relevant memories using vector search
        List<JobMemory> relevantMemories = jobMemoryService.
            searchSimilar(
                jobId, userQuery, MAX_CONTEXT_MEMORIES);

        if (relevantMemories.isEmpty()) {
            return "No information has been stored for this CAD analysis yet.";
        }

        // 2. Build context from memories
        String context = buildContext(relevantMemories);

        // 3. Generate response using Fireworks AI
        List<Map<String, String>> messages = List.of(
                Map.of("role", "system", "content",
                        "You are a CAD analysis assistant. Answer questions based on the provided context " +
                                "from the CAD analysis. Be specific and reference findings when applicable. " +
                                "If the context doesn't contain enough information to answer, say so."),
                Map.of("role", "user", "content",
                        "Context from CAD analysis:\n\n" + context + "\n\n" +
                                "Question: " + userQuery));

        return fireworksAIService.chatCompletion(messages, 1000, 0.3);
    }

    /**
     * Get the count of memories used for context.
     */
    public int getSourcesCount(String jobId, String userQuery) {
        List<JobMemory> memories = jobMemoryService.searchSimilar(
                jobId, userQuery, MAX_CONTEXT_MEMORIES);
        return memories.size();
    }

    /**
     * Build context string from memories.
     */
    private String buildContext(List<JobMemory> memories) {
        return memories.stream()
                .map(m -> {
                    String category = m.getCategory() != null ? "[" + m.getCategory() + "] " : "";
                    return category + m.getContent();
                })
                .collect(Collectors.joining("\n\n---\n\n"));
    }
}
