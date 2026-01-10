package com.shlawgathon.tactile.backend.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import com.shlawgathon.tactile.backend.websocket.JobWebSocketHandler;

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final JobWebSocketHandler jobWebSocketHandler;

    public WebSocketConfig(JobWebSocketHandler jobWebSocketHandler) {
        this.jobWebSocketHandler = jobWebSocketHandler;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(jobWebSocketHandler, "/ws/jobs/{jobId}")
                .setAllowedOrigins("*");
    }
}
