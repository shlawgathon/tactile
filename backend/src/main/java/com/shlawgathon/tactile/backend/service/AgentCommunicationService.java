package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.dto.ResumeCheckpoint;
import com.shlawgathon.tactile.backend.dto.StartJobRequest;
import com.shlawgathon.tactile.backend.model.Checkpoint;
import com.shlawgathon.tactile.backend.model.Job;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

import com.fasterxml.jackson.databind.ObjectMapper;

@Service
public class AgentCommunicationService {

    private static final Logger log = LoggerFactory.getLogger(AgentCommunicationService.class);

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final FileStorageService fileStorageService;

    @Value("${agent.module.url}")
    private String agentModuleUrl;

    @Value("${server.port:8080}")
    private String serverPort;

    public AgentCommunicationService(FileStorageService fileStorageService, ObjectMapper objectMapper) {
        // Force HTTP/1.1 - Uvicorn doesn't support HTTP/2 upgrade
        this.httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .build();
        this.objectMapper = objectMapper;
        this.fileStorageService = fileStorageService;
    }

    /**
     * Start a new job on the agent module.
     */
    public void startJob(Job job) {
        try {
            StartJobRequest request = StartJobRequest.builder()
                    .jobId(job.getId())
                    .fileUrl(fileStorageService.getFileUrl(job.getFileStorageId()))
                    .manufacturingProcess(job.getManufacturingProcess() != null
                            ? job.getManufacturingProcess().name()
                            : "FDM_3D_PRINTING")
                    .material(job.getMaterial())
                    .callbackUrl(getCallbackUrl(job.getId()))
                    .resumeFromCheckpoint(null)
                    .build();

            log.info("[AGENT START] Job: {} | FileUrl: {} | Process: {}",
                    job.getId(), request.getFileUrl(), request.getManufacturingProcess());

            sendToAgent("/agent/jobs/start", request);
        } catch (Exception e) {
            log.error("[AGENT START] Failed to start job: {} - {}", job.getId(), e.getMessage(), e);
            throw new RuntimeException("Failed to start agent job: " + e.getMessage(), e);
        }
    }

    /**
     * Resume a job from checkpoint.
     */
    public void resumeJob(Job job, Checkpoint checkpoint) {
        try {
            StartJobRequest.StartJobRequestBuilder builder = StartJobRequest.builder()
                    .jobId(job.getId())
                    .fileUrl(fileStorageService.getFileUrl(job.getFileStorageId()))
                    .manufacturingProcess(job.getManufacturingProcess() != null
                            ? job.getManufacturingProcess().name()
                            : "FDM_3D_PRINTING")
                    .material(job.getMaterial())
                    .callbackUrl(getCallbackUrl(job.getId()));

            if (checkpoint != null) {
                builder.resumeFromCheckpoint(
                        ResumeCheckpoint.builder()
                                .stage(checkpoint.getStage())
                                .state(checkpoint.getState())
                                .intermediateResults(checkpoint.getIntermediateResults())
                                .build());
            }

            sendToAgent("/agent/jobs/start", builder.build());
        } catch (Exception e) {
            log.error("Failed to resume job on agent module: {}", job.getId(), e);
        }
    }

    /**
     * Cancel a running job.
     */
    public void cancelJob(String jobId) {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(agentModuleUrl + "/agent/jobs/" + jobId + "/cancel"))
                    .header("Content-Type", "application/json")
                    .DELETE()
                    .build();

            httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                    .thenAccept(response -> {
                        if (response.statusCode() != 200) {
                            log.warn("Failed to cancel job: {} - Status: {}", jobId, response.statusCode());
                        }
                    });
        } catch (Exception e) {
            log.error("Failed to cancel job on agent module: {}", jobId, e);
        }
    }

    private void sendToAgent(String path, Object body) throws Exception {
        String jsonBody = objectMapper.writeValueAsString(body);
        String fullUrl = agentModuleUrl + path;

        log.info("[AGENT HTTP] Sending request to: {}", fullUrl);
        log.info("[AGENT HTTP] Request body: {}", jsonBody);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(fullUrl))
                .header("Content-Type", "application/json")
                .header("Accept", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();

        httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenAccept(response -> {
                    if (response.statusCode() == 200 || response.statusCode() == 202) {
                        log.info("[AGENT HTTP] Success for path: {}", path);
                    } else {
                        log.warn("[AGENT HTTP] Error status: {} for path: {}, body: {}",
                                response.statusCode(), path, response.body());
                    }
                })
                .exceptionally(e -> {
                    log.error("[AGENT HTTP] Failed to communicate with agent at {}: {}", fullUrl, e.getMessage());
                    return null;
                });
    }

    private String getCallbackUrl(String jobId) {
        return "http://localhost:" + serverPort + "/internal/jobs/" + jobId + "/callback";
    }
}
