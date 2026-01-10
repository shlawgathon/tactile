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
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Service for generating vector embeddings using Voyage AI.
 */
@Service
public class VoyageEmbeddingService {

    private static final Logger log = LoggerFactory.getLogger(VoyageEmbeddingService.class);

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;

    @Value("${voyage.api.url:https://api.voyageai.com/v1/embeddings}")
    private String apiUrl;

    @Value("${voyage.api.key:}")
    private String apiKey;

    @Value("${voyage.api.model:voyage-3}")
    private String model;

    public VoyageEmbeddingService(ObjectMapper objectMapper) {
        this.httpClient = HttpClient.newHttpClient();
        this.objectMapper = objectMapper;
    }

    /**
     * Generate embedding for a single text.
     */
    public List<Double> generateEmbedding(String text) throws Exception {
        List<List<Double>> embeddings = generateEmbeddings(List.of(text));
        return embeddings.isEmpty() ? new ArrayList<>() : embeddings.get(0);
    }

    /**
     * Generate embeddings for multiple texts.
     */
    public List<List<Double>> generateEmbeddings(List<String> texts) throws Exception {
        if (apiKey == null || apiKey.isBlank()) {
            log.warn("Voyage AI API key not configured, returning empty embeddings");
            return texts.stream()
                    .map(t -> new ArrayList<Double>())
                    .collect(Collectors.toUnmodifiableList());
        }

        Map<String, Object> requestBody = Map.of(
                "input", texts,
                "model", model);

        String jsonBody = objectMapper.writeValueAsString(requestBody);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(apiUrl))
                .header("Accept", "application/json")
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + apiKey)
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();

        log.debug("Sending embedding request to Voyage AI for {} texts", texts.size());

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            log.error("Voyage AI API error: {} - {}", response.statusCode(), response.body());
            throw new RuntimeException("Voyage AI API error: " + response.statusCode());
        }

        JsonNode responseJson = objectMapper.readTree(response.body());
        JsonNode dataArray = responseJson.path("data");

        List<List<Double>> embeddings = new ArrayList<>();
        for (JsonNode item : dataArray) {
            List<Double> embedding = new ArrayList<>();
            for (JsonNode value : item.path("embedding")) {
                embedding.add(value.asDouble());
            }
            embeddings.add(embedding);
        }

        return embeddings;
    }
}
