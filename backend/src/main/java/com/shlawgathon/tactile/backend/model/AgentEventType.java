package com.shlawgathon.tactile.backend.model;

/**
 * Types of agent events for the activity stream.
 */
public enum AgentEventType {
    ANALYZING, // Agent is examining something
    RUNNING_CODE, // Executing CadQuery code
    TOOL_RESULT, // Result from tool execution
    THINKING, // Agent's reasoning/thought process
    SUGGESTION, // A suggestion was generated
    ERROR, // An error occurred
    MEMORY_STORED, // Memory was persisted
    SUCCESS, // Analysis completed successfully
    GENUI_GEN_SUCCESS // Thesys C1 UI generation completed
}
