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
 * Service for interacting with Thesys C1 API to generate dynamic UI components.
 * The C1 API is OpenAI-compatible and returns UI specifications that can be
 * rendered by the Thesys GenUI SDK on the frontend.
 */
@Service
public class ThesysService {

        private static final Logger log = LoggerFactory.getLogger(ThesysService.class);

        private final HttpClient httpClient;
        private final ObjectMapper objectMapper;

        @Value("${thesys.api.url}")
        private String apiUrl;

        @Value("${thesys.api.key}")
        private String apiKey;

        @Value("${thesys.api.model}")
        private String model;

        public ThesysService(ObjectMapper objectMapper) {
                this.httpClient = HttpClient.newHttpClient();
                this.objectMapper = objectMapper;
        }

        /**
         * Send a chat completion request to Thesys C1 API.
         */
        public String chatCompletion(List<Map<String, String>> messages) throws Exception {
                return chatCompletion(messages, 4096, 0.7);
        }

        /**
         * Send a chat completion request with custom parameters.
         */
        public String chatCompletion(List<Map<String, String>> messages, int maxTokens, double temperature)
                        throws Exception {
                Map<String, Object> requestBody = Map.of(
                                "model", model,
                                "max_tokens", maxTokens,
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

                log.debug("Sending request to Thesys C1 API: {}", apiUrl);

                HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

                // Accept 200 (OK) and 201 (Created) as successful responses
                if (response.statusCode() != 200 && response.statusCode() != 201) {
                        log.error("Thesys C1 API error: {} - {}", response.statusCode(), response.body());
                        throw new RuntimeException("Thesys C1 API error: " + response.statusCode());
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
         * Generate a UI specification from a natural language prompt.
         * 
         * @param prompt  The user's request for UI generation
         * @param context Additional context about the data or use case
         * @return UI specification that can be rendered by GenUI SDK
         */
        public String generateUISpec(String prompt, String context) throws Exception {
                List<Map<String, String>> messages = List.of(
                                Map.of("role", "system", "content",
                                                "You are a UI generation assistant. Generate clean, modern UI components "
                                                                +
                                                                "for displaying manufacturing analysis data. Use appropriate charts, "
                                                                +
                                                                "cards, and data visualizations. Context: " + context),
                                Map.of("role", "user", "content", prompt));

                return chatCompletion(messages, 4096, 0.7);
        }

        /**
         * Generate a visual summary UI for DFM analysis results.
         * 
         * @param analysisResults The DFM analysis results to visualize
         * @return UI specification for the analysis summary
         */
        public String generateDFMSummaryUI(Map<String, Object> analysisResults) throws Exception {
                String resultsJson = objectMapper.writeValueAsString(analysisResults);

                List<Map<String, String>> messages = List.of(
                                Map.of("role", "system", "content",
                                                "You are a DFM (Design for Manufacturing) visualization expert. " +
                                                                "Generate a comprehensive UI dashboard to display CAD analysis results. "
                                                                +
                                                                "Include: issue severity charts, manufacturing recommendations, "
                                                                +
                                                                "cost impact indicators, and actionable fix suggestions."),
                                Map.of("role", "user", "content",
                                                "Generate a visual summary dashboard for these DFM analysis results:\n"
                                                                + resultsJson));

                return chatCompletion(messages, 8192, 0.5);
        }

        /**
         * Generate UI for displaying a specific manufacturing issue.
         * 
         * @param issueType    The type of manufacturing issue
         * @param issueDetails Details about the issue
         * @param severity     Issue severity level
         * @return UI specification for the issue display
         */
        public String generateIssueUI(String issueType, String issueDetails, String severity) throws Exception {
                List<Map<String, String>> messages = List.of(
                                Map.of("role", "system", "content",
                                                "You are a UI generation assistant specializing in manufacturing issue displays. "
                                                                +
                                                                "Create clear, actionable UI components that help engineers understand "
                                                                +
                                                                "and resolve manufacturing issues."),
                                Map.of("role", "user", "content",
                                                String.format("Generate a UI component for this manufacturing issue:\n"
                                                                +
                                                                "Type: %s\nSeverity: %s\nDetails: %s",
                                                                issueType, severity, issueDetails)));

                return chatCompletion(messages, 2048, 0.6);
        }
}
