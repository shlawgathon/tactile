package com.shlawgathon.tactile.backend.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.util.List;
import java.util.Map;

/**
 * DFM Rule document for Design for Manufacturing checks.
 * Supports vector search via embedding field.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "dfm_rules")
public class DFMRule {

    @Id
    private String id;

    @Indexed
    private String name;

    @Indexed
    private ManufacturingProcess process;

    private String category;
    private String description;
    private Map<String, Object> parameters;
    private Severity severity;

    // Vector embedding for semantic search (Voyage AI)
    private List<Double> embedding;
}
