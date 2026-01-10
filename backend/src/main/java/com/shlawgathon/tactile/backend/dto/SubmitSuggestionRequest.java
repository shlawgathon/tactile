package com.shlawgathon.tactile.backend.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request DTO for submitting a suggestion incrementally.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SubmitSuggestionRequest {

    private String issueId;
    private String description;
    private String expectedImprovement;
    private int priority;
    private String codeSnippet;
}
