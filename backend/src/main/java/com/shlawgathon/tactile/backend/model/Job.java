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
import java.util.ArrayList;
import java.util.List;

/**
 * Job document representing a CAD analysis job.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "jobs")
public class Job {

    @Id
    private String id;

    @Indexed
    private String userId;

    @Builder.Default
    private JobStatus status = JobStatus.QUEUED;

    // Input
    private String originalFilename;
    private String fileStorageId;
    private ManufacturingProcess manufacturingProcess;
    private String material;

    // Progress
    private String currentStage;

    @Builder.Default
    private int progressPercent = 0;

    @Builder.Default
    private List<String> stagesCompleted = new ArrayList<>();

    // Timing
    @CreatedDate
    private Instant createdAt;

    private Instant startedAt;
    private Instant completedAt;

    // Error handling
    private String errorMessage;

    @Builder.Default
    private int retryCount = 0;

    private String lastCheckpointId;

    // Results summary
    private Integer totalIssues;
    private Integer criticalIssues;
    private Integer warnings;
}
