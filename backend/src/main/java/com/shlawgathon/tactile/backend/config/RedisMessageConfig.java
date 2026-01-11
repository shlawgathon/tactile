package com.shlawgathon.tactile.backend.config;

import com.shlawgathon.tactile.backend.pubsub.JobEventSubscriber;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.listener.PatternTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.data.redis.listener.adapter.MessageListenerAdapter;

/**
 * Redis Pub/Sub configuration for distributed WebSocket event broadcasting.
 */
@Configuration
public class RedisMessageConfig {

    public static final String JOB_EVENTS_CHANNEL = "tactile:job-events";

    @Bean
    public RedisMessageListenerContainer redisMessageListenerContainer(
            RedisConnectionFactory connectionFactory,
            MessageListenerAdapter messageListenerAdapter) {

        RedisMessageListenerContainer container = new RedisMessageListenerContainer();
        container.setConnectionFactory(connectionFactory);
        container.addMessageListener(messageListenerAdapter, new PatternTopic(JOB_EVENTS_CHANNEL));
        return container;
    }

    @Bean
    public MessageListenerAdapter messageListenerAdapter(JobEventSubscriber subscriber) {
        return new MessageListenerAdapter(subscriber, "handleMessage");
    }
}
