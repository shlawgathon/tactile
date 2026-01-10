package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.model.AnalysisResult;
import com.shlawgathon.tactile.backend.model.Suggestion;
import com.shlawgathon.tactile.backend.repository.AnalysisResultRepository;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Optional;

@Service
public class AnalysisResultService {

    private final AnalysisResultRepository analysisResultRepository;

    public AnalysisResultService(AnalysisResultRepository analysisResultRepository) {
        this.analysisResultRepository = analysisResultRepository;
    }

    public AnalysisResult save(AnalysisResult result) {
        return analysisResultRepository.save(result);
    }

    public Optional<AnalysisResult> findById(String id) {
        return analysisResultRepository.findById(id);
    }

    public Optional<AnalysisResult> findByJobId(String jobId) {
        return analysisResultRepository.findByJobId(jobId);
    }

    public boolean existsByJobId(String jobId) {
        return analysisResultRepository.existsByJobId(jobId);
    }

    public void deleteByJobId(String jobId) {
        analysisResultRepository.deleteByJobId(jobId);
    }

    /**
     * Add a suggestion to an existing analysis result, or create one if it doesn't
     * exist.
     */
    public AnalysisResult addSuggestion(String jobId, Suggestion suggestion) {
        AnalysisResult result = analysisResultRepository.findByJobId(jobId)
                .orElseGet(() -> AnalysisResult.builder()
                        .jobId(jobId)
                        .suggestions(new ArrayList<>())
                        .build());

        if (result.getSuggestions() == null) {
            result.setSuggestions(new ArrayList<>());
        }
        result.getSuggestions().add(suggestion);

        return analysisResultRepository.save(result);
    }
}
