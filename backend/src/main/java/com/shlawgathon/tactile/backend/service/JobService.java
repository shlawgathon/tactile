package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.dto.CreateJobRequest;
import com.shlawgathon.tactile.backend.model.Job;
import com.shlawgathon.tactile.backend.model.JobStatus;
import com.shlawgathon.tactile.backend.repository.JobRepository;
import com.shlawgathon.tactile.backend.websocket.JobWebSocketHandler;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Service
public class JobService {

    private final JobRepository jobRepository;
    private final AgentCommunicationService agentCommunicationService;
    private final CheckpointService checkpointService;
    private final JobWebSocketHandler webSocketHandler;

    public JobService(JobRepository jobRepository,
            AgentCommunicationService agentCommunicationService,
            CheckpointService checkpointService,
            JobWebSocketHandler webSocketHandler) {
        this.jobRepository = jobRepository;
        this.agentCommunicationService = agentCommunicationService;
        this.checkpointService = checkpointService;
        this.webSocketHandler = webSocketHandler;
    }

    /**
     * Create a new analysis job.
     */
    public Job createJob(String userId, CreateJobRequest request) {
        Job job = Job.builder()
                .userId(userId)
                .status(JobStatus.QUEUED)
                .originalFilename(request.getOriginalFilename())
                .fileStorageId(request.getFileStorageId())
                .manufacturingProcess(request.getManufacturingProcess())
                .material(request.getMaterial())
                .currentStage("QUEUED")
                .build();

        job = jobRepository.save(job);

        // Send to agent module and update status
        try {
            agentCommunicationService.startJob(job);
            // Update to PARSING status to indicate job is being processed
            job.setStatus(JobStatus.PARSING);
            job.setCurrentStage("PARSING");
            job.setStartedAt(Instant.now());
            job = jobRepository.save(job);
            webSocketHandler.sendJobUpdate(job.getId(), job);
        } catch (Exception e) {
            // If agent communication fails, job stays queued for retry
            job.setErrorMessage("Failed to start agent: " + e.getMessage());
            jobRepository.save(job);
        }

        return job;
    }

    public Optional<Job> findById(String id) {
        return jobRepository.findById(id);
    }

    public List<Job> findByUserId(String userId) {
        return jobRepository.findByUserId(userId);
    }

    public Page<Job> findByUserId(String userId, Pageable pageable) {
        return jobRepository.findByUserId(userId, pageable);
    }

    public List<Job> findByStatus(JobStatus status) {
        return jobRepository.findByStatus(status);
    }

    /**
     * Update job status with WebSocket notification.
     */
    public Job updateStatus(String jobId, JobStatus status, String currentStage, int progressPercent) {
        return jobRepository.findById(jobId).map(job -> {
            job.setStatus(status);
            job.setCurrentStage(currentStage);
            job.setProgressPercent(progressPercent);

            if (status == JobStatus.PARSING && job.getStartedAt() == null) {
                job.setStartedAt(Instant.now());
            }

            if (status == JobStatus.COMPLETED || status == JobStatus.FAILED) {
                job.setCompletedAt(Instant.now());
            }

            Job savedJob = jobRepository.save(job);
            webSocketHandler.sendJobUpdate(jobId, savedJob);
            return savedJob;
        }).orElseThrow(() -> new RuntimeException("Job not found: " + jobId));
    }

    /**
     * Mark a stage as completed.
     */
    public Job completeStage(String jobId, String stageName) {
        return jobRepository.findById(jobId).map(job -> {
            job.getStagesCompleted().add(stageName);
            return jobRepository.save(job);
        }).orElseThrow(() -> new RuntimeException("Job not found: " + jobId));
    }

    /**
     * Mark job as completed with result summary.
     */
    public Job completeJob(String jobId, int totalIssues, int criticalIssues, int warnings) {
        return jobRepository.findById(jobId).map(job -> {
            job.setStatus(JobStatus.COMPLETED);
            job.setCompletedAt(Instant.now());
            job.setProgressPercent(100);
            job.setTotalIssues(totalIssues);
            job.setCriticalIssues(criticalIssues);
            job.setWarnings(warnings);

            Job savedJob = jobRepository.save(job);
            webSocketHandler.sendJobUpdate(jobId, savedJob);
            return savedJob;
        }).orElseThrow(() -> new RuntimeException("Job not found: " + jobId));
    }

    /**
     * Mark job as failed.
     */
    public Job failJob(String jobId, String errorMessage) {
        return jobRepository.findById(jobId).map(job -> {
            job.setStatus(JobStatus.FAILED);
            job.setErrorMessage(errorMessage);
            job.setCompletedAt(Instant.now());

            Job savedJob = jobRepository.save(job);
            webSocketHandler.sendJobUpdate(jobId, savedJob);
            return savedJob;
        }).orElseThrow(() -> new RuntimeException("Job not found: " + jobId));
    }

    /**
     * Cancel a job.
     */
    public Job cancelJob(String jobId) {
        return jobRepository.findById(jobId).map(job -> {
            if (job.getStatus() == JobStatus.COMPLETED || job.getStatus() == JobStatus.CANCELLED) {
                throw new IllegalStateException("Cannot cancel job in status: " + job.getStatus());
            }

            job.setStatus(JobStatus.CANCELLED);
            job.setCompletedAt(Instant.now());

            // Notify agent module
            agentCommunicationService.cancelJob(jobId);

            Job savedJob = jobRepository.save(job);
            webSocketHandler.sendJobUpdate(jobId, savedJob);
            return savedJob;
        }).orElseThrow(() -> new RuntimeException("Job not found: " + jobId));
    }

    /**
     * Resume a failed job from checkpoint.
     */
    public Job resumeJob(String jobId, String checkpointId) {
        return jobRepository.findById(jobId).map(job -> {
            if (job.getStatus() != JobStatus.FAILED) {
                throw new IllegalStateException("Can only resume failed jobs");
            }

            job.setStatus(JobStatus.QUEUED);
            job.setErrorMessage(null);
            job.setRetryCount(job.getRetryCount() + 1);

            Job savedJob = jobRepository.save(job);

            // Get checkpoint and resume
            var checkpoint = checkpointId != null
                    ? checkpointService.findById(checkpointId)
                    : checkpointService.getLatestCheckpoint(jobId);

            agentCommunicationService.resumeJob(savedJob, checkpoint.orElse(null));

            webSocketHandler.sendJobUpdate(jobId, savedJob);
            return savedJob;
        }).orElseThrow(() -> new RuntimeException("Job not found: " + jobId));
    }

    /**
     * Delete a job permanently.
     */
    public void deleteJob(String jobId) {
        jobRepository.findById(jobId).ifPresent(job -> {
            // Cancel the job first if it's running
            if (job.getStatus() == JobStatus.QUEUED || job.getStatus() == JobStatus.PARSING || 
                job.getStatus() == JobStatus.ANALYZING) {
                try {
                    agentCommunicationService.cancelJob(jobId);
                } catch (Exception e) {
                    // Ignore cancellation errors during deletion
                }
            }
            jobRepository.deleteById(jobId);
        });
    }

    public void delete(String id) {
        jobRepository.deleteById(id);
    }
}
