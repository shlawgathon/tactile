package com.shlawgathon.tactile.backend.websocket;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.http.server.ServletServerHttpRequest;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.server.HandshakeInterceptor;

import jakarta.servlet.http.HttpSession;
import java.util.Map;

/**
 * Interceptor to extract HTTP session and security context during WebSocket handshake.
 * This ensures the Principal is available in the WebSocket session.
 */
@Component
public class HttpSessionHandshakeInterceptor implements HandshakeInterceptor {

    private static final Logger log = LoggerFactory.getLogger(HttpSessionHandshakeInterceptor.class);
    public static final String SESSION_ATTR = "HTTP_SESSION";
    public static final String PRINCIPAL_ATTR = "PRINCIPAL";

    @Override
    public boolean beforeHandshake(ServerHttpRequest request, ServerHttpResponse response,
                                   WebSocketHandler wsHandler, Map<String, Object> attributes) {
        
        if (request instanceof ServletServerHttpRequest servletRequest) {
            HttpSession session = servletRequest.getServletRequest().getSession(false);
            
            if (session != null) {
                attributes.put(SESSION_ATTR, session);
                log.debug("HTTP session found during WebSocket handshake: {}", session.getId());
            } else {
                log.warn("No HTTP session found during WebSocket handshake");
            }

            // Get current authentication from security context
            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            if (auth != null && auth.isAuthenticated() && !"anonymousUser".equals(auth.getPrincipal())) {
                attributes.put(PRINCIPAL_ATTR, auth);
                log.debug("Authentication found during WebSocket handshake: {}", auth.getName());
                return true;
            } else {
                log.warn("No valid authentication found during WebSocket handshake");
                // Still allow the connection - handler will check and close if needed
                return true;
            }
        }

        log.warn("Request is not a ServletServerHttpRequest");
        return true;
    }

    @Override
    public void afterHandshake(ServerHttpRequest request, ServerHttpResponse response,
                               WebSocketHandler wsHandler, Exception exception) {
        if (exception != null) {
            log.error("WebSocket handshake failed", exception);
        }
    }
}
