package com.shlawgathon.tactile.backend.repository;

import com.shlawgathon.tactile.backend.model.AgentEvent;
import com.shlawgathon.tactile.backend.model.AgentEventType;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * Repository for agent events.
 */
@Repository
public interface AgentEventRepository extends MongoRepository<AgentEvent, String> {

    List<AgentEvent> findByJobIdOrderByCreatedAtAsc(String jobId);

    List<AgentEvent> findByJobIdAndTypeOrderByCreatedAtAsc(String jobId, AgentEventType type);

    void deleteByJobId(String jobId);
}
