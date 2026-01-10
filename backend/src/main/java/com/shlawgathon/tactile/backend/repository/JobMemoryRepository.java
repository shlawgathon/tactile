package com.shlawgathon.tactile.backend.repository;

import com.shlawgathon.tactile.backend.model.JobMemory;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * Repository for job memories.
 */
@Repository
public interface JobMemoryRepository extends MongoRepository<JobMemory, String> {

    List<JobMemory> findByJobId(String jobId);

    List<JobMemory> findByJobIdAndCategory(String jobId, String category);

    void deleteByJobId(String jobId);
}
