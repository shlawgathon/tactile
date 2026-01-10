package com.shlawgathon.tactile.backend.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * DFM issue found during analysis.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Issue {
    private String ruleId;
    private String ruleName;
    private Severity severity;
    private String description;
    private List<String> affectedFeatures;
    private String recommendation;
    private boolean autoFixAvailable;
}
