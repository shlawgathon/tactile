package com.shlawgathon.tactile.backend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.shlawgathon.tactile.backend.dto.PaymentRequirement;
import com.shlawgathon.tactile.backend.model.SubscriptionTier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.Signature;
import java.security.spec.PKCS8EncodedKeySpec;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Service for x402 payment protocol integration with CDP Facilitator API.
 */
@Service
public class X402Service {

    private static final Logger log = LoggerFactory.getLogger(X402Service.class);

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;

    @Value("${cdp.api.url}")
    private String cdpApiUrl;

    @Value("${cdp.api.key-name}")
    private String cdpKeyName;

    @Value("${cdp.api.key-secret}")
    private String cdpKeySecret;

    @Value("${cdp.x402.pay-to-address}")
    private String payToAddress;

    @Value("${cdp.x402.network}")
    private String network;

    @Value("${cdp.x402.asset}")
    private String asset;

    @Value("${cdp.x402.prices.pro}")
    private String proPriceUsd;

    @Value("${cdp.x402.prices.enterprise}")
    private String enterprisePriceUsd;

    public X402Service(ObjectMapper objectMapper) {
        this.httpClient = HttpClient.newHttpClient();
        this.objectMapper = objectMapper;
    }

    /**
     * Build the payment requirement for a given target tier.
     */
    public PaymentRequirement buildPaymentRequirement(SubscriptionTier targetTier) {
        String price = switch (targetTier) {
            case PRO -> "$" + proPriceUsd;
            case ENTERPRISE -> "$" + enterprisePriceUsd;
            default -> throw new IllegalArgumentException("Cannot upgrade to FREE tier");
        };

        return PaymentRequirement.builder()
                .scheme("exact")
                .network(network)
                .price(price)
                .payTo(payToAddress)
                .asset(asset)
                .description("Upgrade to " + targetTier.name() + " tier")
                .build();
    }

    /**
     * Build the full PAYMENT-REQUIRED response payload.
     */
    public PaymentRequirement.PaymentRequiredResponse buildPaymentRequiredResponse(SubscriptionTier targetTier) {
        return PaymentRequirement.PaymentRequiredResponse.builder()
                .accepts(List.of(buildPaymentRequirement(targetTier)))
                .build();
    }

    /**
     * Verify a payment using the CDP Facilitator API.
     *
     * @param paymentPayload The base64-encoded payment payload from
     *                       PAYMENT-SIGNATURE header
     * @param requirement    The payment requirement to verify against
     * @return True if payment is valid
     */
    public boolean verifyPayment(String paymentPayload, PaymentRequirement requirement) {
        try {
            Map<String, Object> requestBody = Map.of(
                    "x402Version", 2,
                    "paymentPayload", paymentPayload,
                    "paymentRequirements", Map.of(
                            "scheme", requirement.getScheme(),
                            "network", requirement.getNetwork(),
                            "maxAmountRequired", requirement.getPrice().replace("$", ""),
                            "resource", "/api/users/upgrade",
                            "description", requirement.getDescription(),
                            "mimeType", "application/json",
                            "outputSchema", Map.of(),
                            "payTo", requirement.getPayTo(),
                            "asset", requirement.getAsset()));

            String jsonBody = objectMapper.writeValueAsString(requestBody);
            String jwt = generateJwt();

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(cdpApiUrl + "/v2/x402/verify"))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + jwt)
                    .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                JsonNode responseJson = objectMapper.readTree(response.body());
                return responseJson.path("valid").asBoolean(false);
            } else {
                log.error("CDP verify API error: {} - {}", response.statusCode(), response.body());
                return false;
            }
        } catch (Exception e) {
            log.error("Failed to verify payment", e);
            return false;
        }
    }

    /**
     * Settle a payment using the CDP Facilitator API.
     *
     * @param paymentPayload The base64-encoded payment payload from
     *                       PAYMENT-SIGNATURE header
     * @param requirement    The payment requirement
     * @return Settlement response with transaction ID, or null if failed
     */
    public SettlementResult settlePayment(String paymentPayload, PaymentRequirement requirement) {
        try {
            Map<String, Object> requestBody = Map.of(
                    "x402Version", 2,
                    "paymentPayload", paymentPayload,
                    "paymentRequirements", Map.of(
                            "scheme", requirement.getScheme(),
                            "network", requirement.getNetwork(),
                            "maxAmountRequired", requirement.getPrice().replace("$", ""),
                            "resource", "/api/users/upgrade",
                            "description", requirement.getDescription(),
                            "mimeType", "application/json",
                            "outputSchema", Map.of(),
                            "payTo", requirement.getPayTo(),
                            "asset", requirement.getAsset()));

            String jsonBody = objectMapper.writeValueAsString(requestBody);
            String jwt = generateJwt();

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(cdpApiUrl + "/v2/x402/settle"))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + jwt)
                    .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                JsonNode responseJson = objectMapper.readTree(response.body());
                return new SettlementResult(
                        true,
                        responseJson.path("transactionHash").asText(null),
                        responseJson.path("networkId").asText(null));
            } else {
                log.error("CDP settle API error: {} - {}", response.statusCode(), response.body());
                return new SettlementResult(false, null, null);
            }
        } catch (Exception e) {
            log.error("Failed to settle payment", e);
            return new SettlementResult(false, null, null);
        }
    }

    /**
     * Generate a JWT for CDP API authentication.
     * Uses ES256 signing with the CDP API key.
     */
    private String generateJwt() throws Exception {
        long now = Instant.now().getEpochSecond();
        String nonce = UUID.randomUUID().toString();

        // JWT Header
        Map<String, Object> header = Map.of(
                "alg", "ES256",
                "kid", cdpKeyName,
                "typ", "JWT",
                "nonce", nonce);

        // JWT Payload
        Map<String, Object> payload = Map.of(
                "sub", cdpKeyName,
                "iss", "cdp",
                "aud", List.of("cdp_service"),
                "nbf", now,
                "exp", now + 120, // 2 minute expiry
                "uris", List.of(cdpApiUrl + "/v2/x402/*"));

        String headerBase64 = base64UrlEncode(objectMapper.writeValueAsBytes(header));
        String payloadBase64 = base64UrlEncode(objectMapper.writeValueAsBytes(payload));
        String signingInput = headerBase64 + "." + payloadBase64;

        // Sign with ES256
        String signature = signEs256(signingInput, cdpKeySecret);

        return signingInput + "." + signature;
    }

    private String signEs256(String data, String keyInput) throws Exception {
        // Clean the key input: remove PEM headers and whitespace
        String cleanKey = keyInput
                .replace("-----BEGIN EC PRIVATE KEY-----", "")
                .replace("-----END EC PRIVATE KEY-----", "")
                .replace("-----BEGIN PRIVATE KEY-----", "")
                .replace("-----END PRIVATE KEY-----", "")
                .replaceAll("\\s+", "");

        byte[] keyBytes = Base64.getDecoder().decode(cleanKey);
        java.security.PrivateKey privateKey = null;
        KeyFactory keyFactory = KeyFactory.getInstance("EC");

        try {
            // 1. Try treating it as a standard PKCS8 key (standard PEM body)
            PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(keyBytes);
            privateKey = keyFactory.generatePrivate(keySpec);
        } catch (Exception e) {
            // 2. Fallback: Treat as raw private key scalar (32 or 64 bytes)
            // CDP sometimes returns just the raw bytes which need wrapping
            log.debug("Failed to parse key as PKCS8, attempting raw format construction", e);

            byte[] privateKeyBytes;
            if (keyBytes.length == 64) {
                // Raw format: first 32 bytes are the private scalar
                privateKeyBytes = new byte[32];
                System.arraycopy(keyBytes, 0, privateKeyBytes, 0, 32);
            } else if (keyBytes.length == 32) {
                privateKeyBytes = keyBytes;
            } else {
                throw new IllegalArgumentException("Invalid key length for raw format: " + keyBytes.length);
            }

            // Build PKCS8 encoded key for EC P-256 manually
            // PKCS8 header for P-256 EC private key
            byte[] pkcs8Header = new byte[]{
                    0x30, (byte) 0x41, 0x02, 0x01, 0x00, 0x30, 0x13, 0x06, 0x07,
                    0x2a, (byte) 0x86, 0x48, (byte) 0xce, 0x3d, 0x02, 0x01, 0x06, 0x08,
                    0x2a, (byte) 0x86, 0x48, (byte) 0xce, 0x3d, 0x03, 0x01, 0x07, 0x04, 0x27,
                    0x30, 0x25, 0x02, 0x01, 0x01, 0x04, 0x20
            };

            byte[] pkcs8Key = new byte[pkcs8Header.length + privateKeyBytes.length];
            System.arraycopy(pkcs8Header, 0, pkcs8Key, 0, pkcs8Header.length);
            System.arraycopy(privateKeyBytes, 0, pkcs8Key, pkcs8Header.length, privateKeyBytes.length);

            PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(pkcs8Key);
            privateKey = keyFactory.generatePrivate(keySpec);
        }

        Signature sig = Signature.getInstance("SHA256withECDSA");
        sig.initSign(privateKey);
        sig.update(data.getBytes(StandardCharsets.UTF_8));
        byte[] signatureBytes = sig.sign();

        // Convert from DER to P1363 format (fixed 64 bytes for ES256)
        byte[] p1363Signature = derToP1363(signatureBytes);
        return base64UrlEncode(p1363Signature);
    }

    private byte[] derToP1363(byte[] derSignature) {
        // Simple DER to P1363 conversion for ES256 (32+32 = 64 bytes)
        int offset = 3;
        int rLength = derSignature[offset++] & 0xff;
        byte[] r = new byte[32];
        if (rLength > 32) {
            System.arraycopy(derSignature, offset + (rLength - 32), r, 0, 32);
        } else {
            System.arraycopy(derSignature, offset, r, 32 - rLength, rLength);
        }
        offset += rLength + 1;

        int sLength = derSignature[offset++] & 0xff;
        byte[] s = new byte[32];
        if (sLength > 32) {
            System.arraycopy(derSignature, offset + (sLength - 32), s, 0, 32);
        } else {
            System.arraycopy(derSignature, offset, s, 32 - sLength, sLength);
        }

        byte[] result = new byte[64];
        System.arraycopy(r, 0, result, 0, 32);
        System.arraycopy(s, 0, result, 32, 32);
        return result;
    }

    private String base64UrlEncode(byte[] data) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(data);
    }

    /**
     * Result of a payment settlement operation.
     */
    public record SettlementResult(boolean success, String transactionHash, String networkId) {
    }
}
