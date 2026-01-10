package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.BaseE2ETest;
import com.shlawgathon.tactile.backend.model.JobMemory;
import com.shlawgathon.tactile.backend.repository.AgentEventRepository;
import com.shlawgathon.tactile.backend.repository.JobMemoryRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.MockBean;

import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

class JobMemoryServiceE2ETest extends BaseE2ETest {

    @Autowired
    private JobMemoryService jobMemoryService;

    @Autowired
    private JobMemoryRepository jobMemoryRepository;

    @Autowired
    private AgentEventRepository agentEventRepository;

    @MockBean
    private VoyageEmbeddingService voyageEmbeddingService;

    @BeforeEach
    void setUp() throws Exception {
        jobMemoryRepository.deleteAll();
        agentEventRepository.deleteAll();
        when(voyageEmbeddingService.generateEmbedding(anyString()))
                .thenReturn(Collections.nCopies(1024, 0.5));
    }

    @Test
    void shouldStoreMemoryWithEmbedding() {
        JobMemory memory = jobMemoryService.storeMemory(
                "job-mem-1",
                "The model has an overhang angle of 65 degrees",
                "geometry",
                Map.of("angle", 65));

        assertThat(memory.getId()).isNotNull();
        assertThat(memory.getJobId()).isEqualTo("job-mem-1");
        assertThat(memory.getContent()).contains("overhang");
        assertThat(memory.getEmbedding()).hasSize(1024);
        assertThat(memory.getEmbedding().get(0)).isEqualTo(0.5);
    }

    @Test
    void shouldStoreMemoryWithCategory() {
        JobMemory memory = jobMemoryService.storeMemory(
                "job-mem-2",
                "Material is ABS with 20% infill",
                "material",
                null);

        assertThat(memory.getCategory()).isEqualTo("material");
    }

    @Test
    void shouldGetMemoriesByJobId() {
        jobMemoryService.storeMemory("job-mem-3", "Memory 1", "geometry", null);
        jobMemoryService.storeMemory("job-mem-3", "Memory 2", "issue", null);
        jobMemoryService.storeMemory("job-mem-3", "Memory 3", "geometry", null);

        List<JobMemory> memories = jobMemoryService.getMemories("job-mem-3");

        assertThat(memories).hasSize(3);
    }

    @Test
    void shouldGetMemoriesByCategory() {
        jobMemoryService.storeMemory("job-mem-4", "Geometry info", "geometry", null);
        jobMemoryService.storeMemory("job-mem-4", "Issue found", "issue", null);
        jobMemoryService.storeMemory("job-mem-4", "More geometry", "geometry", null);

        List<JobMemory> geometryMemories = jobMemoryService.getMemoriesByCategory(
                "job-mem-4", "geometry");

        assertThat(geometryMemories).hasSize(2);
        assertThat(geometryMemories).allMatch(m -> m.getCategory().equals("geometry"));
    }

    @Test
    void shouldHandleEmbeddingServiceFailure() throws Exception {
        // Mock embedding service to throw exception
        when(voyageEmbeddingService.generateEmbedding(anyString()))
                .thenThrow(new RuntimeException("API error"));

        // Should still store memory (without embedding)
        JobMemory memory = jobMemoryService.storeMemory(
                "job-mem-5",
                "Content when embedding fails",
                "test",
                null);

        assertThat(memory.getId()).isNotNull();
        assertThat(memory.getContent()).isEqualTo("Content when embedding fails");
        // Embedding should be null when service fails
        assertThat(memory.getEmbedding()).isNull();
    }

    @Test
    void shouldCreateEventWhenMemoryStored() {
        jobMemoryService.storeMemory(
                "job-mem-6",
                "This memory should create an event",
                "geometry",
                null);

        // Verify an event was created
        var events = agentEventRepository.findByJobIdOrderByCreatedAtAsc("job-mem-6");
        assertThat(events).isNotEmpty();
        assertThat(events.get(0).getType().name()).isEqualTo("MEMORY_STORED");
    }
}
