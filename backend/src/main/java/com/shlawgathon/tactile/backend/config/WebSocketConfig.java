package com.shlawgathon.tactile.backend.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import com.shlawgathon.tactile.backend.websocket.HttpSessionHandshakeInterceptor;
import com.shlawgathon.tactile.backend.websocket.JobWebSocketHandler;
import com.shlawgathon.tactile.backend.websocket.PublicJobWebSocketHandler;

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final JobWebSocketHandler jobWebSocketHandler;
    private final PublicJobWebSocketHandler publicJobWebSocketHandler;
    private final HttpSessionHandshakeInterceptor httpSessionHandshakeInterceptor;

    @Value("${frontend.url:http://localhost:3000}")
    private String frontendUrl;

    public WebSocketConfig(JobWebSocketHandler jobWebSocketHandler,
            PublicJobWebSocketHandler publicJobWebSocketHandler,
            HttpSessionHandshakeInterceptor httpSessionHandshakeInterceptor) {
        this.jobWebSocketHandler = jobWebSocketHandler;
        this.publicJobWebSocketHandler = publicJobWebSocketHandler;
        this.httpSessionHandshakeInterceptor = httpSessionHandshakeInterceptor;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        // Internal WebSocket for agent module (no auth required - uses API key)
        registry.addHandler(jobWebSocketHandler, "/ws/jobs/{jobId}")
                .setAllowedOrigins("*");

        // Public WebSocket for frontend (requires OAuth session)
        // Uses handshake interceptor to extract HTTP session and security context
        registry.addHandler(publicJobWebSocketHandler, "/ws/public/jobs/{jobId}")
                .addInterceptors(httpSessionHandshakeInterceptor)
                .setAllowedOrigins(frontendUrl);
    }
}
