package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.BaseE2ETest;
import com.shlawgathon.tactile.backend.dto.CheckpointRequest;
import com.shlawgathon.tactile.backend.model.Checkpoint;
import com.shlawgathon.tactile.backend.repository.CheckpointRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class CheckpointServiceE2ETest extends BaseE2ETest {

    @Autowired
    private CheckpointService checkpointService;

    @Autowired
    private CheckpointRepository checkpointRepository;

    @BeforeEach
    void setUp() {
        checkpointRepository.deleteAll();
    }

    @Test
    void shouldSaveCheckpoint() {
        // Given
        CheckpointRequest request = CheckpointRequest.builder()
                .stage("PARSE")
                .stageIndex(0)
                .state(Map.of("parsedFaces", 42))
                .reasoningTrace(List.of("Started parsing", "Found 42 faces"))
                .intermediateResults(Map.of("faceCount", 42))
                .recoverable(true)
                .build();

        // When
        Checkpoint saved = checkpointService.saveCheckpoint("job123", request);

        // Then
        assertNotNull(saved.getId());
        assertEquals("job123", saved.getJobId());
        assertEquals("PARSE", saved.getStage());
        assertEquals(0, saved.getStageIndex());
        assertTrue(saved.isRecoverable());
    }

    @Test
    void shouldFindCheckpointsByJobId() {
        // Given
        CheckpointRequest parse = CheckpointRequest.builder()
                .stage("PARSE")
                .stageIndex(0)
                .state(Map.of("step", "parse"))
                .reasoningTrace(List.of())
                .recoverable(true)
                .build();

        CheckpointRequest analyze = CheckpointRequest.builder()
                .stage("ANALYZE")
                .stageIndex(1)
                .state(Map.of("step", "analyze"))
                .reasoningTrace(List.of())
                .recoverable(true)
                .build();

        checkpointService.saveCheckpoint("job456", parse);
        checkpointService.saveCheckpoint("job456", analyze);

        // When
        var checkpoints = checkpointService.findByJobId("job456");

        // Then
        assertEquals(2, checkpoints.size());
    }

    @Test
    void shouldGetLatestCheckpoint() {
        // Given
        CheckpointRequest first = CheckpointRequest.builder()
                .stage("PARSE")
                .stageIndex(0)
                .state(Map.of())
                .reasoningTrace(List.of())
                .recoverable(true)
                .build();

        CheckpointRequest second = CheckpointRequest.builder()
                .stage("ANALYZE")
                .stageIndex(1)
                .state(Map.of())
                .reasoningTrace(List.of())
                .recoverable(true)
                .build();

        CheckpointRequest third = CheckpointRequest.builder()
                .stage("SUGGEST")
                .stageIndex(2)
                .state(Map.of())
                .reasoningTrace(List.of())
                .recoverable(true)
                .build();

        checkpointService.saveCheckpoint("job789", first);
        checkpointService.saveCheckpoint("job789", second);
        checkpointService.saveCheckpoint("job789", third);

        // When
        var latest = checkpointService.getLatestCheckpoint("job789");

        // Then
        assertTrue(latest.isPresent());
        assertEquals("SUGGEST", latest.get().getStage());
        assertEquals(2, latest.get().getStageIndex());
    }

    @Test
    void shouldDeleteCheckpointsByJobId() {
        // Given
        CheckpointRequest request = CheckpointRequest.builder()
                .stage("PARSE")
                .stageIndex(0)
                .state(Map.of())
                .reasoningTrace(List.of())
                .recoverable(true)
                .build();

        checkpointService.saveCheckpoint("job-to-delete", request);
        checkpointService.saveCheckpoint("job-to-delete", request);
        assertEquals(2, checkpointService.findByJobId("job-to-delete").size());

        // When
        checkpointService.deleteByJobId("job-to-delete");

        // Then
        assertEquals(0, checkpointService.findByJobId("job-to-delete").size());
    }
}
