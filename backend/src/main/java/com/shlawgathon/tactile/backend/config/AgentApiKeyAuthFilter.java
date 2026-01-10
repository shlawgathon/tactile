package com.shlawgathon.tactile.backend.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * Filter to authenticate agent API requests using X-Agent-Api-Key header.
 * Only applies to /internal/** endpoints.
 */
@Component
public class AgentApiKeyAuthFilter extends OncePerRequestFilter {

    private static final String AGENT_API_KEY_HEADER = "X-Agent-Api-Key";

    @Value("${agent.api.key:}")
    private String agentApiKey;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {

        String requestPath = request.getRequestURI();

        // Only apply to /internal/** endpoints
        if (!requestPath.startsWith("/internal/")) {
            filterChain.doFilter(request, response);
            return;
        }

        // If no API key is configured, allow the request (development mode)
        if (agentApiKey == null || agentApiKey.isBlank()) {
            filterChain.doFilter(request, response);
            return;
        }

        String providedKey = request.getHeader(AGENT_API_KEY_HEADER);

        if (providedKey == null || providedKey.isBlank()) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json");
            response.getWriter().write("{\"error\":\"Missing X-Agent-Api-Key header\"}");
            return;
        }

        if (!agentApiKey.equals(providedKey)) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json");
            response.getWriter().write("{\"error\":\"Invalid API key\"}");
            return;
        }

        // API key is valid, continue
        filterChain.doFilter(request, response);
    }
}
