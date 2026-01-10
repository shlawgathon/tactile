package com.shlawgathon.tactile.backend.repository;

import com.shlawgathon.tactile.backend.model.Job;
import com.shlawgathon.tactile.backend.model.JobStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface JobRepository extends MongoRepository<Job, String> {

    List<Job> findByUserId(String userId);

    Page<Job> findByUserId(String userId, Pageable pageable);

    List<Job> findByStatus(JobStatus status);

    List<Job> findByUserIdAndStatus(String userId, JobStatus status);

    long countByUserIdAndStatus(String userId, JobStatus status);

    List<Job> findByStatusIn(List<JobStatus> statuses);
}
