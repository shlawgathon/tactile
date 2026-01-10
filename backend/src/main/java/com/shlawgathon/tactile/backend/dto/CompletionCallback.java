package com.shlawgathon.tactile.backend.dto;

import com.shlawgathon.tactile.backend.model.CodeSnippet;
import com.shlawgathon.tactile.backend.model.Issue;
import com.shlawgathon.tactile.backend.model.Suggestion;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * Callback from Agent Module on job completion.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Job completion callback from Agent Module")
public class CompletionCallback {

    @Schema(description = "Whether the job succeeded")
    private boolean success;

    @Schema(description = "Analysis results")
    private ResultsPayload results;

    @Schema(description = "Output files")
    private OutputFiles outputFiles;

    /**
     * Results payload containing analysis data.
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Analysis results payload")
    public static class ResultsPayload {

        @Schema(description = "Geometry summary")
        private GeometrySummary geometrySummary;

        @Schema(description = "Issues found")
        private List<Issue> issues;

        @Schema(description = "Suggestions for fixes")
        private List<Suggestion> suggestions;

        @Schema(description = "Generated code snippets")
        private List<CodeSnippet> generatedCode;

        @Schema(description = "Markdown analysis report from agent")
        private String markdownReport;
    }

    /**
     * Geometry summary from analysis.
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Geometry summary")
    public static class GeometrySummary {

        @Schema(description = "Bounding box dimensions")
        private Map<String, Double> boundingBox;

        @Schema(description = "Volume in cubic units")
        private Double volume;

        @Schema(description = "Surface area in square units")
        private Double surfaceArea;

        @Schema(description = "Number of faces")
        private Integer faceCount;

        @Schema(description = "Number of edges")
        private Integer edgeCount;
    }

    /**
     * Output files from analysis.
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Output files from analysis")
    public static class OutputFiles {

        @Schema(description = "Modified STEP file (base64)")
        private String modifiedStep;

        @Schema(description = "Preview STL file (base64)")
        private String previewStl;

        @Schema(description = "Preview images (base64)")
        private List<String> previewImages;
    }
}
