package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.dto.CheckpointRequest;
import com.shlawgathon.tactile.backend.model.Checkpoint;
import com.shlawgathon.tactile.backend.repository.CheckpointRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class CheckpointService {

    private final CheckpointRepository checkpointRepository;

    public CheckpointService(CheckpointRepository checkpointRepository) {
        this.checkpointRepository = checkpointRepository;
    }

    /**
     * Save a checkpoint from agent callback.
     */
    public Checkpoint saveCheckpoint(String jobId, CheckpointRequest request) {
        Checkpoint checkpoint = Checkpoint.builder()
                .jobId(jobId)
                .stage(request.getStage())
                .stageIndex(request.getStageIndex())
                .state(request.getState())
                .reasoningTrace(request.getReasoningTrace())
                .intermediateResults(request.getIntermediateResults())
                .recoverable(request.isRecoverable())
                .build();

        return checkpointRepository.save(checkpoint);
    }

    public Optional<Checkpoint> findById(String id) {
        return checkpointRepository.findById(id);
    }

    public List<Checkpoint> findByJobId(String jobId) {
        return checkpointRepository.findByJobId(jobId);
    }

    /**
     * Get the latest checkpoint for a job.
     */
    public Optional<Checkpoint> getLatestCheckpoint(String jobId) {
        return checkpointRepository.findFirstByJobIdOrderByStageIndexDesc(jobId);
    }

    /**
     * Get all checkpoints for a job in reverse order.
     */
    public List<Checkpoint> getCheckpointsDescending(String jobId) {
        return checkpointRepository.findByJobIdOrderByStageIndexDesc(jobId);
    }

    public void deleteByJobId(String jobId) {
        checkpointRepository.deleteByJobId(jobId);
    }
}
