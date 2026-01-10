'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { AgentEvent } from '../services/jobs';

// WebSocket URL - derive from API_URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api';
const getWsUrl = () => {
    // Convert http(s) to ws(s)
    const baseUrl = API_URL.endsWith('/api') ? API_URL.slice(0, -4) : API_URL;
    return baseUrl.replace(/^http/, 'ws');
};

interface WebSocketMessage {
    type: string;
    jobId: string;
    data: Record<string, any>;
}

interface UseJobEventsResult {
    events: AgentEvent[];
    isConnected: boolean;
    connectionError: string | null;
}

/**
 * React hook for real-time job event streaming via WebSocket.
 * 
 * Connects to the public WebSocket endpoint and receives agent events in real-time.
 * Falls back to polling if WebSocket connection fails.
 * 
 * @param jobId - The job ID to subscribe to
 * @param initialEvents - Optional initial events to start with (from REST API)
 */
export const useJobEvents = (
    jobId: string | null,
    initialEvents: AgentEvent[] = []
): UseJobEventsResult => {
    const [events, setEvents] = useState<AgentEvent[]>(initialEvents);
    const [isConnected, setIsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const reconnectAttemptsRef = useRef(0);

    // Parse WebSocket message and add to events
    const handleMessage = useCallback((event: MessageEvent) => {
        try {
            const message: WebSocketMessage = JSON.parse(event.data);

            if (message.type === 'AGENT_EVENT') {
                const newEvent: AgentEvent = {
                    id: message.data.eventId,
                    jobId: message.jobId,
                    type: message.data.eventType,
                    title: message.data.title,
                    content: message.data.content,
                    metadata: message.data.metadata,
                    createdAt: message.data.createdAt,
                };

                setEvents(prev => {
                    // Avoid duplicates based on event ID
                    if (prev.some(e => e.id === newEvent.id)) {
                        return prev;
                    }
                    return [...prev, newEvent];
                });
            } else if (message.type === 'CONNECTED') {
                console.log('[WebSocket] Connected to job event stream:', jobId);
            }
        } catch (error) {
            console.error('[WebSocket] Failed to parse message:', error);
        }
    }, [jobId]);

    // Connect to WebSocket
    const connect = useCallback(() => {
        if (!jobId) return;

        const wsUrl = `${getWsUrl()}/ws/public/jobs/${jobId}`;
        console.log('[WebSocket] Connecting to:', wsUrl);

        try {
            const socket = new WebSocket(wsUrl);

            socket.onopen = () => {
                console.log('[WebSocket] Connection established');
                setIsConnected(true);
                setConnectionError(null);
                reconnectAttemptsRef.current = 0;
            };

            socket.onmessage = handleMessage;

            socket.onclose = (event) => {
                console.log('[WebSocket] Connection closed:', event.code, event.reason);
                setIsConnected(false);
                wsRef.current = null;

                // Attempt to reconnect with exponential backoff
                if (reconnectAttemptsRef.current < 5) {
                    const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
                    console.log(`[WebSocket] Reconnecting in ${delay}ms...`);
                    reconnectTimeoutRef.current = setTimeout(() => {
                        reconnectAttemptsRef.current++;
                        connect();
                    }, delay);
                } else {
                    setConnectionError('Failed to connect after multiple attempts');
                }
            };

            socket.onerror = (error) => {
                console.error('[WebSocket] Error:', error);
                setConnectionError('WebSocket connection error');
            };

            wsRef.current = socket;
        } catch (error) {
            console.error('[WebSocket] Failed to create connection:', error);
            setConnectionError('Failed to create WebSocket connection');
        }
    }, [jobId, handleMessage]);

    // Connect on mount, cleanup on unmount
    useEffect(() => {
        if (jobId) {
            connect();
        }

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
            }
        };
    }, [jobId, connect]);

    // Update events when initialEvents changes
    useEffect(() => {
        if (initialEvents.length > 0) {
            setEvents(prev => {
                // Merge initial events with existing, avoiding duplicates
                const existingIds = new Set(prev.map(e => e.id));
                const newEvents = initialEvents.filter(e => !existingIds.has(e.id));
                if (newEvents.length > 0) {
                    return [...prev, ...newEvents].sort(
                        (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
                    );
                }
                return prev;
            });
        }
    }, [initialEvents]);

    return {
        events,
        isConnected,
        connectionError,
    };
};
