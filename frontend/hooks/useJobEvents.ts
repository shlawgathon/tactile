'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { AgentEvent, getJobEvents } from '../services/jobs';

// WebSocket URL - derive from API_URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api';
const getWsUrl = () => {
    // Convert http(s) to ws(s)
    const baseUrl = API_URL.endsWith('/api') ? API_URL.slice(0, -4) : API_URL;
    return baseUrl.replace(/^http/, 'ws');
};

// WebSocket close codes
const WS_AUTH_REQUIRED = 4001;
const WS_POLICY_VIOLATION = 1008;

// Polling interval when WebSocket fails (5 seconds)
const POLLING_INTERVAL = 5000;

interface WebSocketMessage {
    type: string;
    jobId: string;
    data: Record<string, unknown>;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'polling' | 'error';

export interface ConnectionError {
    type: 'auth' | 'network' | 'unknown';
    message: string;
}

interface UseJobEventsResult {
    events: AgentEvent[];
    isConnected: boolean;
    connectionStatus: ConnectionStatus;
    connectionError: ConnectionError | null;
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
    // Sort initial events by creation time to ensure proper order
    const [events, setEvents] = useState<AgentEvent[]>(
        initialEvents.sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())
    );
    const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting');
    const [connectionError, setConnectionError] = useState<ConnectionError | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const reconnectAttemptsRef = useRef(0);
    const isPollingRef = useRef(false);
    const lastEventIdRef = useRef<string | null>(null);

    // Track the last known event ID to fetch only new events when polling
    useEffect(() => {
        if (events.length > 0) {
            lastEventIdRef.current = events[events.length - 1].id;
        }
    }, [events]);

    // Merge new events with existing ones, avoiding duplicates
    const mergeEvents = useCallback((newEvents: AgentEvent[]) => {
        setEvents(prev => {
            const existingIds = new Set(prev.map(e => e.id));
            const uniqueNewEvents = newEvents.filter(e => !existingIds.has(e.id));
            if (uniqueNewEvents.length > 0) {
                return [...prev, ...uniqueNewEvents].sort(
                    (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
                );
            }
            return prev;
        });
    }, []);

    // Poll for events via REST API
    const pollEvents = useCallback(async () => {
        if (!jobId) return;

        try {
            const fetchedEvents = await getJobEvents(jobId);
            if (fetchedEvents.length > 0) {
                mergeEvents(fetchedEvents);
            }
        } catch (error) {
            console.error('[Polling] Failed to fetch events:', error);
        }
    }, [jobId, mergeEvents]);

    // Start polling fallback
    const startPolling = useCallback(() => {
        if (isPollingRef.current || !jobId) return;

        console.log('[Polling] Starting fallback polling...');
        isPollingRef.current = true;
        setConnectionStatus('polling');

        // Initial poll
        pollEvents();

        // Set up interval
        pollingIntervalRef.current = setInterval(pollEvents, POLLING_INTERVAL);
    }, [jobId, pollEvents]);

    // Stop polling
    const stopPolling = useCallback(() => {
        if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
        }
        isPollingRef.current = false;
    }, []);

    // Parse WebSocket message and add to events
    const handleMessage = useCallback((event: MessageEvent) => {
        try {
            const message: WebSocketMessage = JSON.parse(event.data);

            if (message.type === 'AGENT_EVENT') {
                const newEvent: AgentEvent = {
                    id: message.data.eventId as string,
                    jobId: message.jobId,
                    type: message.data.eventType as string,
                    title: message.data.title as string,
                    content: message.data.content as string,
                    metadata: message.data.metadata as Record<string, unknown>,
                    createdAt: message.data.createdAt as string,
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
            } else if (message.type === 'AUTH_ERROR') {
                console.warn('[WebSocket] Authentication error:', message.data);
                setConnectionError({
                    type: 'auth',
                    message: 'Authentication required. Please refresh the page to log in again.'
                });
            }
        } catch (error) {
            console.error('[WebSocket] Failed to parse message:', error);
        }
    }, [jobId]);

    // Connect to WebSocket
    const connect = useCallback(() => {
        if (!jobId) return;

        // Don't try to connect if we're already polling due to auth error
        if (connectionError?.type === 'auth') {
            startPolling();
            return;
        }

        const wsUrl = `${getWsUrl()}/ws/public/jobs/${jobId}`;
        console.log('[WebSocket] Connecting to:', wsUrl);
        setConnectionStatus('connecting');

        try {
            const socket = new WebSocket(wsUrl);

            socket.onopen = () => {
                console.log('[WebSocket] Connection established');
                setConnectionStatus('connected');
                setConnectionError(null);
                reconnectAttemptsRef.current = 0;
                stopPolling();
            };

            socket.onmessage = handleMessage;

            socket.onclose = (event) => {
                console.log('[WebSocket] Connection closed:', event.code, event.reason);
                wsRef.current = null;

                // Check if it's an authentication error
                if (event.code === WS_AUTH_REQUIRED || event.code === WS_POLICY_VIOLATION) {
                    console.warn('[WebSocket] Authentication failed, falling back to polling');
                    setConnectionError({
                        type: 'auth',
                        message: 'Session expired. Using polling for updates.'
                    });
                    startPolling();
                    return;
                }

                // Attempt to reconnect with exponential backoff
                if (reconnectAttemptsRef.current < 5) {
                    const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
                    console.log(`[WebSocket] Reconnecting in ${delay}ms... (attempt ${reconnectAttemptsRef.current + 1}/5)`);
                    setConnectionStatus('connecting');
                    reconnectTimeoutRef.current = setTimeout(() => {
                        reconnectAttemptsRef.current++;
                        connect();
                    }, delay);
                } else {
                    console.warn('[WebSocket] Max reconnection attempts reached, falling back to polling');
                    setConnectionError({
                        type: 'network',
                        message: 'WebSocket connection failed. Using polling for updates.'
                    });
                    startPolling();
                }
            };

            socket.onerror = (error) => {
                console.error('[WebSocket] Error:', error);
                // Don't set error here - onclose will handle it
            };

            wsRef.current = socket;
        } catch (error) {
            console.error('[WebSocket] Failed to create connection:', error);
            setConnectionError({
                type: 'unknown',
                message: 'Failed to create WebSocket connection'
            });
            startPolling();
        }
    }, [jobId, handleMessage, connectionError?.type, startPolling, stopPolling]);

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
            stopPolling();
        };
    }, [jobId, connect, stopPolling]);

    // Update events when initialEvents changes
    useEffect(() => {
            if (initialEvents.length > 0) {
            // Sort and set initial events, ensuring old events appear first
            setEvents(prev => {
                const allEvents = [...initialEvents, ...prev];
                const uniqueEvents = Array.from(
                    new Map(allEvents.map(e => [e.id, e])).values()
                );
                return uniqueEvents.sort(
                    (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
                );
            });
        }
    }, [initialEvents]);

    return {
        events,
        isConnected: connectionStatus === 'connected',
        connectionStatus,
        connectionError,
    };
};
