package com.shlawgathon.tactile.backend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.List;
import java.util.Map;

/**
 * Service for interacting with Fireworks AI LLM.
 */
@Service
public class FireworksAIService {

    private static final Logger log = LoggerFactory.getLogger(FireworksAIService.class);

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;

    @Value("${fireworks.api.url}")
    private String apiUrl;

    @Value("${fireworks.api.key}")
    private String apiKey;

    @Value("${fireworks.api.model}")
    private String model;

    public FireworksAIService(ObjectMapper objectMapper) {
        this.httpClient = HttpClient.newHttpClient();
        this.objectMapper = objectMapper;
    }

    /**
     * Send a chat completion request to Fireworks AI.
     */
    public String chatCompletion(List<Map<String, String>> messages) throws Exception {
        return chatCompletion(messages, 4096, 0.6);
    }

    /**
     * Send a chat completion request with custom parameters.
     */
    public String chatCompletion(List<Map<String, String>> messages, int maxTokens, double temperature)
            throws Exception {
        Map<String, Object> requestBody = Map.of(
                "model", model,
                "max_tokens", maxTokens,
                "top_p", 1,
                "top_k", 40,
                "presence_penalty", 0,
                "frequency_penalty", 0,
                "temperature", temperature,
                "messages", messages);

        String jsonBody = objectMapper.writeValueAsString(requestBody);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(apiUrl))
                .header("Accept", "application/json")
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + apiKey)
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            log.error("Fireworks AI API error: {} - {}", response.statusCode(), response.body());
            throw new RuntimeException("Fireworks AI API error: " + response.statusCode());
        }

        JsonNode responseJson = objectMapper.readTree(response.body());
        return responseJson
                .path("choices")
                .path(0)
                .path("message")
                .path("content")
                .asText();
    }

    /**
     * Generate issue description using LLM.
     */
    public String generateIssueDescription(String issueType, Map<String, Object> context) throws Exception {
        List<Map<String, String>> messages = List.of(
                Map.of("role", "system", "content",
                        "You are a DFM (Design for Manufacturing) expert. Generate clear, actionable descriptions for manufacturing issues found in CAD models."),
                Map.of("role", "user", "content",
                        "Issue type: " + issueType + "\nContext: " + objectMapper.writeValueAsString(context) +
                                "\n\nProvide a clear description of this issue and its impact on manufacturing."));

        return chatCompletion(messages, 500, 0.3);
    }

    /**
     * Generate fix suggestions using LLM.
     */
    public String generateFixSuggestion(String issueDescription, String manufacturingProcess) throws Exception {
        List<Map<String, String>> messages = List.of(
                Map.of("role", "system", "content",
                        "You are a CAD/CAM expert specializing in " + manufacturingProcess +
                                ". Generate practical fix suggestions with CadQuery Python code when possible."),
                Map.of("role", "user", "content",
                        "Issue: " + issueDescription +
                                "\n\nProvide a detailed fix suggestion with step-by-step instructions and CadQuery code if applicable."));

        return chatCompletion(messages, 1000, 0.5);
    }

    /**
     * Generate CadQuery code for a specific fix.
     */
    public String generateCadQueryCode(String fixDescription, String geometryContext) throws Exception {
        List<Map<String, String>> messages = List.of(
                Map.of("role", "system", "content",
                        "You are a CadQuery expert. Generate only valid Python CadQuery code. " +
                                "Do not include explanations, only code. The code should be executable."),
                Map.of("role", "user", "content",
                        "Fix to implement: " + fixDescription +
                                "\nGeometry context: " + geometryContext +
                                "\n\nGenerate CadQuery Python code to implement this fix."));

        return chatCompletion(messages, 800, 0.2);
    }
}
