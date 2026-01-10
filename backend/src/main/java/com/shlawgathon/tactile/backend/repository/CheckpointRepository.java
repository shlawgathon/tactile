package com.shlawgathon.tactile.backend.repository;

import com.shlawgathon.tactile.backend.model.Checkpoint;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface CheckpointRepository extends MongoRepository<Checkpoint, String> {

    List<Checkpoint> findByJobId(String jobId);

    List<Checkpoint> findByJobIdOrderByStageIndexDesc(String jobId);

    Optional<Checkpoint> findFirstByJobIdOrderByStageIndexDesc(String jobId);

    void deleteByJobId(String jobId);
}
