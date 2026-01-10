package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.model.AnalysisResult;
import com.shlawgathon.tactile.backend.repository.AnalysisResultRepository;
import org.springframework.stereotype.Service;

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
}
