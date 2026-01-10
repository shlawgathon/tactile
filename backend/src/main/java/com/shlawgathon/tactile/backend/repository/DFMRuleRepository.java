package com.shlawgathon.tactile.backend.repository;

import com.shlawgathon.tactile.backend.model.DFMRule;
import com.shlawgathon.tactile.backend.model.ManufacturingProcess;
import com.shlawgathon.tactile.backend.model.Severity;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DFMRuleRepository extends MongoRepository<DFMRule, String> {

    List<DFMRule> findByProcess(ManufacturingProcess process);

    List<DFMRule> findByProcessAndCategory(ManufacturingProcess process, String category);

    List<DFMRule> findByProcessAndSeverity(ManufacturingProcess process, Severity severity);

    List<DFMRule> findByCategory(String category);
}
