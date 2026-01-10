package com.shlawgathon.tactile.backend.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Generated CadQuery code snippet.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CodeSnippet {
    private String id;
    private String description;
    private String code;
    private String language;
    private boolean validated;
}
