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
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Analysis result document containing DFM findings and suggestions.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "analysis_results")
public class AnalysisResult {

    @Id
    private String id;

    @Indexed(unique = true)
    private String jobId;

    // Geometry summary
    private BoundingBox boundingBox;
    private Double volume;
    private Double surfaceArea;
    private Integer faceCount;
    private Integer edgeCount;

    // Issues found
    @Builder.Default
    private List<Issue> issues = new ArrayList<>();

    @Builder.Default
    private Map<String, Integer> issuesBySeverity = new HashMap<>();

    // Suggestions
    @Builder.Default
    private List<Suggestion> suggestions = new ArrayList<>();

    @Builder.Default
    private List<CodeSnippet> generatedCodeSnippets = new ArrayList<>();

    // Output files
    private String modifiedStepFileId;

    @Builder.Default
    private List<String> previewImageIds = new ArrayList<>();

    // Agent-generated markdown analysis report
    private String markdownReport;

    // Thesys C1 UI-converted report (for frontend rendering)
    private String c1UiReport;

    @CreatedDate
    private Instant createdAt;
}
