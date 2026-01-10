package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.model.User;
import com.shlawgathon.tactile.backend.repository.UserRepository;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class UserService {

    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    /**
     * Find or create a user from OAuth2 login.
     */
    public User findOrCreateFromOAuth(OAuth2User oAuth2User, String provider) {
        String oauthId = oAuth2User.getAttribute("id").toString();

        return userRepository.findByOauthProviderAndOauthId(provider, oauthId)
                .orElseGet(() -> createUserFromOAuth(oAuth2User, provider, oauthId));
    }

    private User createUserFromOAuth(OAuth2User oAuth2User, String provider, String oauthId) {
        User user = User.builder()
                .email(oAuth2User.getAttribute("email"))
                .name(oAuth2User.getAttribute("name") != null
                        ? oAuth2User.getAttribute("name")
                        : oAuth2User.getAttribute("login"))
                .avatarUrl(oAuth2User.getAttribute("avatar_url"))
                .oauthProvider(provider)
                .oauthId(oauthId)
                .build();

        return userRepository.save(user);
    }

    public Optional<User> findById(String id) {
        return userRepository.findById(id);
    }

    public Optional<User> findByEmail(String email) {
        return userRepository.findByEmail(email);
    }

    public List<User> findAll() {
        return userRepository.findAll();
    }

    public User save(User user) {
        return userRepository.save(user);
    }

    public void incrementUsage(String userId) {
        userRepository.findById(userId).ifPresent(user -> {
            user.setUsageThisMonth(user.getUsageThisMonth() + 1);
            userRepository.save(user);
        });
    }

    public void delete(String id) {
        userRepository.deleteById(id);
    }
}
