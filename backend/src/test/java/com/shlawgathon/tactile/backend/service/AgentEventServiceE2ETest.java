package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.BaseE2ETest;
import com.shlawgathon.tactile.backend.model.AgentEvent;
import com.shlawgathon.tactile.backend.model.AgentEventType;
import com.shlawgathon.tactile.backend.repository.AgentEventRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class AgentEventServiceE2ETest extends BaseE2ETest {

    @Autowired
    private AgentEventService agentEventService;

    @Autowired
    private AgentEventRepository agentEventRepository;

    @BeforeEach
    void setUp() {
        agentEventRepository.deleteAll();
    }

    @Test
    void shouldCreateEventWithAllFields() {
        Map<String, Object> metadata = Map.of(
                "feature", "overhang",
                "angle", 60.5);

        AgentEvent event = agentEventService.createEvent(
                "job-1",
                AgentEventType.ANALYZING,
                "Analyzing overhang",
                "Found overhang at 60.5 degrees",
                metadata);

        assertThat(event.getId()).isNotNull();
        assertThat(event.getJobId()).isEqualTo("job-1");
        assertThat(event.getType()).isEqualTo(AgentEventType.ANALYZING);
        assertThat(event.getTitle()).isEqualTo("Analyzing overhang");
        assertThat(event.getContent()).isEqualTo("Found overhang at 60.5 degrees");
        assertThat(event.getMetadata()).containsEntry("feature", "overhang");
    }

    @Test
    void shouldAutoPopulateCreatedAt() {
        AgentEvent event = agentEventService.createEvent(
                "job-2",
                AgentEventType.RUNNING_CODE,
                "Running CadQuery",
                "Executing analysis script",
                null);

        assertThat(event.getCreatedAt()).isNotNull();
    }

    @Test
    void shouldGetEventsInChronologicalOrder() throws InterruptedException {
        // Create events with slight delays to ensure ordering
        agentEventService.createEvent("job-3", AgentEventType.ANALYZING,
                "First", "First event", null);
        Thread.sleep(10); // Small delay
        agentEventService.createEvent("job-3", AgentEventType.RUNNING_CODE,
                "Second", "Second event", null);
        Thread.sleep(10);
        agentEventService.createEvent("job-3", AgentEventType.SUGGESTION,
                "Third", "Third event", null);

        List<AgentEvent> events = agentEventService.getEventsByJobId("job-3");

        assertThat(events).hasSize(3);
        assertThat(events.get(0).getTitle()).isEqualTo("First");
        assertThat(events.get(1).getTitle()).isEqualTo("Second");
        assertThat(events.get(2).getTitle()).isEqualTo("Third");
    }

    @Test
    void shouldFilterByEventType() {
        agentEventService.createEvent("job-4", AgentEventType.ANALYZING,
                "Analyze 1", "Content", null);
        agentEventService.createEvent("job-4", AgentEventType.RUNNING_CODE,
                "Run code", "Content", null);
        agentEventService.createEvent("job-4", AgentEventType.ANALYZING,
                "Analyze 2", "Content", null);

        List<AgentEvent> analyzingEvents = agentEventService.getEventsByJobIdAndType(
                "job-4", AgentEventType.ANALYZING);

        assertThat(analyzingEvents).hasSize(2);
        assertThat(analyzingEvents).allMatch(e -> e.getType() == AgentEventType.ANALYZING);
    }

    @Test
    void shouldIsolateEventsByJobId() {
        agentEventService.createEvent("job-A", AgentEventType.ANALYZING,
                "Event A1", "Content", null);
        agentEventService.createEvent("job-A", AgentEventType.ANALYZING,
                "Event A2", "Content", null);
        agentEventService.createEvent("job-B", AgentEventType.ANALYZING,
                "Event B1", "Content", null);

        List<AgentEvent> jobAEvents = agentEventService.getEventsByJobId("job-A");
        List<AgentEvent> jobBEvents = agentEventService.getEventsByJobId("job-B");

        assertThat(jobAEvents).hasSize(2);
        assertThat(jobBEvents).hasSize(1);
        assertThat(jobAEvents).allMatch(e -> e.getJobId().equals("job-A"));
    }
}
