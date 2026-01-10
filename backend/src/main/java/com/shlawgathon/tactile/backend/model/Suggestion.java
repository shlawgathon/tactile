package com.shlawgathon.tactile.backend.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Suggested fix for a DFM issue.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Suggestion {
    private String issueId;
    private String description;
    private String expectedImprovement;
    private int priority;
    private String codeSnippet;
    private boolean validated;
}
