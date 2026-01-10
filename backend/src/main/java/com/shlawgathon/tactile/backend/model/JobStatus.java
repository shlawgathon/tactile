package com.shlawgathon.tactile.backend.model;

/**
 * Status of a CAD analysis job.
 */
public enum JobStatus {
    QUEUED,
    PARSING,
    ANALYZING,
    SUGGESTING,
    VALIDATING,
    COMPLETED,
    FAILED,
    CANCELLED
}
