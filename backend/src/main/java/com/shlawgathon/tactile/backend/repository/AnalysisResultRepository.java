package com.shlawgathon.tactile.backend.repository;

import com.shlawgathon.tactile.backend.model.AnalysisResult;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface AnalysisResultRepository extends MongoRepository<AnalysisResult, String> {

    Optional<AnalysisResult> findByJobId(String jobId);

    boolean existsByJobId(String jobId);

    void deleteByJobId(String jobId);
}
